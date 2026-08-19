"""Tests for the out-of-process CHIRP programmer bridge.

The web UI can reach these functions with attacker-shaped input if a browser
page ever gets the session token, so the validation tests here matter as much
as the happy path. Nothing in this file talks to real hardware.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from wasds150.radios import programmer
from wasds150.radios.programmer import ProgrammerError


# ------------------------------------------------------------ validation --
@pytest.mark.parametrize(
    "port",
    ["COM1", "COM7", "COM255", "/dev/ttyUSB0", "/dev/ttyACM1", "/dev/ttyS0"],
)
def test_valid_ports_accepted(port):
    assert programmer.validate_port(port) == port


@pytest.mark.parametrize(
    "port",
    [
        "",
        "COM",
        "COM7; rm -rf /",
        "COM7 && shutdown",
        "COM7|whoami",
        "$(whoami)",
        "`whoami`",
        "/dev/ttyUSB0; cat /etc/passwd",
        "../../etc/passwd",
        "/dev/../etc/passwd",
        "COM7\nCOM8",
        "COM7 --execute",
        "LPT1",
        "A" * 500,
    ],
)
def test_hostile_ports_rejected(port):
    """A port name becomes a subprocess argument; nothing exotic gets through."""
    with pytest.raises(ProgrammerError):
        programmer.validate_port(port)


@pytest.mark.parametrize("label", ["td-h9", "radio-a", "radio_b", "A1.bak", "x"])
def test_valid_labels_accepted(label):
    assert programmer.validate_label(label) == label


@pytest.mark.parametrize(
    "label",
    [
        "",
        "../escape",
        "dir/sub",
        "dir\\sub",
        "label with space",
        ".hidden",
        "-leading-dash",
        "a" * 100,
        "name;rm -rf /",
        "name\x00null",
    ],
)
def test_hostile_labels_rejected(label):
    """A label becomes part of a backup filename, so no separators or traversal."""
    with pytest.raises(ProgrammerError):
        programmer.validate_label(label)


# ------------------------------------------------------- command building --
@pytest.fixture()
def fake_repo(tmp_path):
    """A repo-shaped tree with a stub interpreter and programmer script."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
    scripts = tmp_path / "scripts" / "radios"
    scripts.mkdir(parents=True)
    (scripts / "program_tdh9.py").write_text("# stub\n", encoding="utf-8")

    venv = tmp_path / programmer.CHIRP_VENV_DIRNAME
    if sys.platform.startswith("win"):
        bindir = venv / "Scripts"
        exe = bindir / "python.exe"
    else:
        bindir = venv / "bin"
        exe = bindir / "python"
    bindir.mkdir(parents=True)
    exe.write_text("", encoding="utf-8")

    modules = tmp_path / ".chirp-modules"
    modules.mkdir()
    (modules / "tdh8_15609.py").write_text("# stub driver\n", encoding="utf-8")
    return tmp_path


def test_status_available_when_everything_present(fake_repo):
    state = programmer.status(fake_repo)
    assert state.available is True
    assert state.reasons == []
    assert state.driver_module is not None


def test_status_reports_missing_venv(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    state = programmer.status(tmp_path)
    assert state.available is False
    assert any("CHIRP interpreter" in reason for reason in state.reasons)


def test_status_is_serializable(fake_repo):
    import json

    payload = json.loads(json.dumps(programmer.status(fake_repo).to_dict()))
    assert payload["available"] is True


def test_build_command_backup_only(fake_repo):
    argv = programmer.build_command(
        port="COM7", label="radio-a", backup_only=True, root=fake_repo
    )
    assert "--backup-only" in argv
    assert "--execute" not in argv
    assert "--csv" not in argv
    assert argv[argv.index("--port") + 1] == "COM7"


def test_build_command_dry_run_omits_execute(fake_repo, tmp_path):
    csv = tmp_path / "plan.csv"
    csv.write_text("Location,Name\n", encoding="utf-8")
    argv = programmer.build_command(port="COM7", csv_path=csv, execute=False, root=fake_repo)
    assert "--csv" in argv
    assert "--execute" not in argv, "a dry run must never pass --execute"


def test_build_command_execute_includes_flag(fake_repo, tmp_path):
    csv = tmp_path / "plan.csv"
    csv.write_text("Location,Name\n", encoding="utf-8")
    argv = programmer.build_command(port="COM7", csv_path=csv, execute=True, root=fake_repo)
    assert "--execute" in argv


def test_build_command_requires_csv_when_writing(fake_repo):
    with pytest.raises(ProgrammerError, match="CSV path is required"):
        programmer.build_command(port="COM7", csv_path=None, root=fake_repo)


def test_build_command_rejects_missing_csv(fake_repo, tmp_path):
    with pytest.raises(ProgrammerError, match="CSV not found"):
        programmer.build_command(
            port="COM7", csv_path=tmp_path / "absent.csv", root=fake_repo
        )


def test_build_command_rejects_bad_port_before_spawning(fake_repo, tmp_path):
    csv = tmp_path / "plan.csv"
    csv.write_text("x\n", encoding="utf-8")
    with pytest.raises(ProgrammerError):
        programmer.build_command(port="COM7 && calc", csv_path=csv, root=fake_repo)


def test_build_command_without_venv_raises(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "scripts").mkdir()
    with pytest.raises(ProgrammerError):
        programmer.build_command(port="COM7", backup_only=True, root=tmp_path)


# --------------------------------------------------------------- running --
def test_run_captures_output(tmp_path):
    """Run a real subprocess, but a harmless one."""
    argv = [sys.executable, "-c", "print('hello from child')"]
    result = programmer.run(argv, root=tmp_path)
    assert result.ok is True
    assert result.returncode == 0
    assert "hello from child" in result.stdout
    assert result.timed_out is False


def test_run_reports_failure(tmp_path):
    argv = [sys.executable, "-c", "import sys; sys.exit(3)"]
    result = programmer.run(argv, root=tmp_path)
    assert result.ok is False
    assert result.returncode == 3


def test_run_times_out(tmp_path):
    argv = [sys.executable, "-c", "import time; time.sleep(30)"]
    result = programmer.run(argv, root=tmp_path, timeout=1)
    assert result.timed_out is True
    assert result.ok is False


def test_run_raises_on_missing_executable(tmp_path):
    with pytest.raises(ProgrammerError):
        programmer.run([str(tmp_path / "definitely-not-here")], root=tmp_path)


def test_run_result_is_serializable(tmp_path):
    import json

    result = programmer.run([sys.executable, "-c", "pass"], root=tmp_path)
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["ok"] is True


# ------------------------------------------------------------ presentation --
def test_describe_command_shortens_repo_paths(fake_repo, tmp_path):
    csv = tmp_path / "plan.csv"
    csv.write_text("x\n", encoding="utf-8")
    argv = programmer.build_command(
        port="COM7", csv_path=csv, execute=True, root=fake_repo
    )
    text = programmer.describe_command(argv, fake_repo)
    assert "--port COM7" in text
    assert "--execute" in text
    # The long absolute interpreter path is shortened to a repo-relative one.
    assert str(fake_repo) not in text


def test_list_serial_ports_returns_list():
    """Must never raise, even with no hardware attached."""
    ports = programmer.list_serial_ports()
    assert isinstance(ports, list)
    for row in ports:
        assert "port" in row


def test_repo_root_finds_this_repository():
    root = programmer.repo_root()
    assert (root / "pyproject.toml").is_file()
