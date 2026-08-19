"""Bridge to the out-of-process CHIRP programmer.

CHIRP is GPL-3 and this package is MIT with zero runtime dependencies, so
CHIRP is never imported here.  It lives in a separate interpreter
(``.venv-chirp``) and is driven as a subprocess, which keeps the licence
boundary at a process edge and keeps ``pip install wasds150`` dependency-free.

Everything in this module treats its arguments as untrusted.  The web UI is
loopback-only and token-authenticated, but a serial port name that reaches a
subprocess is still user input, so ports and labels are validated against
strict patterns and the child is always spawned as an argument vector with
no shell.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

#: Serial port names we are willing to hand to a subprocess.  Windows COM
#: ports and POSIX tty device paths, nothing else.  Anything containing a
#: shell metacharacter, a space, or a path traversal fails this outright.
_PORT_RE = re.compile(r"^(COM[0-9]{1,3}|/dev/tty[A-Za-z0-9._-]{1,32})$")

#: Backup filename prefixes.  These become part of a path, so no separators.
_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

#: Where the CHIRP-capable interpreter is expected to live, relative to the
#: repository root.  CHIRP needs Python >= 3.10; this project supports 3.9.
CHIRP_VENV_DIRNAME = ".venv-chirp"

#: The programmer script, relative to the repository root.
PROGRAMMER_SCRIPT = Path("scripts") / "radios" / "program_tdh9.py"

#: Hard ceiling on a programming run.  A full read-write-verify cycle over a
#: slow clone cable takes roughly two minutes; ten is generous but bounded so
#: a wedged child cannot pin the UI open forever.
DEFAULT_TIMEOUT_SECONDS = 600


class ProgrammerError(RuntimeError):
    """Raised when the programmer cannot be run or rejects its input."""


def repo_root(start: Optional[Path] = None) -> Path:
    """Find the repository root by walking up for a known marker.

    Falls back to the current directory so that running from an installed
    wheel (where ``scripts/`` is absent) degrades to "not available" rather
    than raising.
    """
    here = (start or Path(__file__).resolve()).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").is_file() and (candidate / "scripts").is_dir():
            return candidate
    return Path.cwd()


def chirp_python(root: Optional[Path] = None) -> Optional[Path]:
    """Path to the interpreter inside ``.venv-chirp``, if it exists."""
    base = (root or repo_root()) / CHIRP_VENV_DIRNAME
    for relative in (Path("Scripts") / "python.exe", Path("bin") / "python"):
        candidate = base / relative
        if candidate.is_file():
            return candidate
    return None


def programmer_script(root: Optional[Path] = None) -> Optional[Path]:
    candidate = (root or repo_root()) / PROGRAMMER_SCRIPT
    return candidate if candidate.is_file() else None


def validate_port(port: str) -> str:
    """Return ``port`` if it is a plausible serial device, else raise."""
    text = (port or "").strip()
    if not _PORT_RE.match(text):
        raise ProgrammerError(
            f"invalid serial port {port!r}; expected COM3 or /dev/ttyUSB0"
        )
    return text


def validate_label(label: str) -> str:
    """Return ``label`` if it is safe to use as a filename prefix."""
    text = (label or "").strip()
    if not _LABEL_RE.match(text):
        raise ProgrammerError(
            f"invalid label {label!r}; use letters, digits, dot, dash, underscore"
        )
    return text


@dataclass
class ProgrammerStatus:
    """Whether a flash can be attempted, and why not when it cannot."""

    available: bool
    python_path: Optional[str] = None
    script_path: Optional[str] = None
    driver_module: Optional[str] = None
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "available": self.available,
            "python_path": self.python_path,
            "script_path": self.script_path,
            "driver_module": self.driver_module,
            "reasons": list(self.reasons),
        }


def status(root: Optional[Path] = None) -> ProgrammerStatus:
    """Report whether the out-of-process programmer is usable."""
    base = root or repo_root()
    reasons: List[str] = []

    python = chirp_python(base)
    if python is None:
        reasons.append(
            f"no CHIRP interpreter at {base / CHIRP_VENV_DIRNAME}; "
            "create it with 'python -m venv .venv-chirp' (needs Python 3.10+) "
            "then 'pip install git+https://github.com/kk7ds/chirp.git'"
        )

    script = programmer_script(base)
    if script is None:
        reasons.append(f"programmer script not found at {base / PROGRAMMER_SCRIPT}")

    modules = sorted((base / ".chirp-modules").glob("tdh8*.py")) if base else []
    driver = str(modules[-1]) if modules else None
    if driver is None:
        reasons.append(
            "no TD-H9 driver module fetched; run "
            "'python scripts/radios/fetch_chirp_tdh9_module.py'"
        )

    return ProgrammerStatus(
        available=not reasons,
        python_path=str(python) if python else None,
        script_path=str(script) if script else None,
        driver_module=driver,
        reasons=reasons,
    )


def list_serial_ports() -> List[Dict[str, str]]:
    """Enumerate serial ports without requiring pyserial in this interpreter.

    Uses the Windows registry when available and ``/dev`` globbing elsewhere,
    so the stdlib-only guarantee holds.  Returns an empty list rather than
    raising when nothing can be enumerated.
    """
    ports: List[Dict[str, str]] = []

    if sys.platform.startswith("win"):
        try:
            import winreg  # noqa: PLC0415 - Windows-only, imported lazily

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM"
            )
            try:
                index = 0
                while True:
                    try:
                        source, name, _kind = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    ports.append({"port": str(name), "detail": str(source)})
                    index += 1
            finally:
                winreg.CloseKey(key)
        except (ImportError, OSError):
            return []
    else:
        import glob  # noqa: PLC0415 - only needed on POSIX

        for pattern in ("/dev/ttyUSB*", "/dev/ttyACM*", "/dev/tty.usb*"):
            for path in sorted(glob.glob(pattern)):
                ports.append({"port": path, "detail": ""})

    return sorted(ports, key=lambda row: row["port"])


@dataclass
class ProgrammerRun:
    """Outcome of one subprocess invocation."""

    ok: bool
    command: List[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "command": list(self.command),
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "timed_out": self.timed_out,
        }


def build_command(
    *,
    port: str,
    csv_path: Optional[Path] = None,
    label: str = "td-h9",
    execute: bool = False,
    backup_only: bool = False,
    root: Optional[Path] = None,
) -> List[str]:
    """Assemble the argument vector for one programmer run.

    Exposed separately so the UI can show the exact command it is about to
    run, and so a caller with no ``.venv-chirp`` can still copy and paste it.
    """
    base = root or repo_root()
    python = chirp_python(base)
    script = programmer_script(base)
    if python is None or script is None:
        raise ProgrammerError("; ".join(status(base).reasons))

    argv = [str(python), str(script), "--port", validate_port(port)]
    argv += ["--label", validate_label(label)]

    if backup_only:
        argv.append("--backup-only")
    else:
        if csv_path is None:
            raise ProgrammerError("a CSV path is required unless backup_only is set")
        resolved = Path(csv_path).resolve()
        if not resolved.is_file():
            raise ProgrammerError(f"CSV not found: {resolved}")
        argv += ["--csv", str(resolved)]
        if execute:
            argv.append("--execute")

    return argv


def run(
    argv: List[str],
    *,
    root: Optional[Path] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> ProgrammerRun:
    """Run a prepared programmer command and capture its output.

    Never uses a shell.  ``argv`` must already have come from
    :func:`build_command`, which validates every interpolated value.
    """
    base = root or repo_root()
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        completed = subprocess.run(  # noqa: S603 - argv vector, shell=False
            argv,
            cwd=str(base),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        return ProgrammerRun(
            ok=False,
            command=list(argv),
            returncode=-1,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=f"timed out after {timeout}s",
            timed_out=True,
        )
    except OSError as exc:
        raise ProgrammerError(f"could not start the programmer: {exc}") from exc

    return ProgrammerRun(
        ok=completed.returncode == 0,
        command=list(argv),
        returncode=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )


def describe_command(argv: List[str], root: Optional[Path] = None) -> str:
    """Render an argv as a copy-pasteable shell command."""
    base = root or repo_root()

    def shorten(token: str) -> str:
        try:
            relative = Path(token).relative_to(base)
        except (ValueError, OSError):
            return token
        return str(relative)

    parts = []
    for token in argv:
        text = shorten(token)
        parts.append(f'"{text}"' if " " in text else text)
    return " ".join(parts)


def which_chirp_hint() -> str:
    """A short hint for setting up the CHIRP venv, for error surfaces."""
    python = shutil.which("python") or shutil.which("python3") or "python"
    return (
        f"{python} -m venv .venv-chirp && "
        ".venv-chirp/Scripts/pip install git+https://github.com/kk7ds/chirp.git"
    )
