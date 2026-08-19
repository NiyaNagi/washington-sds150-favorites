"""Program a TIDRADIO TD-H9 from a CHIRP CSV file.

This is the only part of the project that talks to hardware, and it is kept
out of the ``wasds150`` package on purpose.  The package stays stdlib-only and
produces files; CHIRP is a GPL-3.0 third-party dependency living in its own
virtual environment, and only this script imports it.

Why a script rather than ``chirpc``: CHIRP's command line can download and
upload a whole image, but it has no way to import a CSV into one.  Driving
CHIRP as a library is the same code path the GUI's copy-and-paste uses.

Safety rules built in, in order:

1. **Read the radio first and save that image.**  A CSV cannot describe
   calibration data, the Normal/HAM/GMRS mode byte, or any of the settings
   the radio needs; those survive only by being read back off the radio and
   written into the image we upload.
2. **Never upload without a verified backup on disk.**
3. **Dry run by default.**  Writing requires ``--execute``.
4. **Read back and compare** after writing.

Usage::

    python scripts/radios/program_tdh9.py --port COM3 --backup-only
    python scripts/radios/program_tdh9.py --port COM3 --csv plan.csv
    python scripts/radios/program_tdh9.py --port COM3 --csv plan.csv --execute
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

MODULE_DIR = Path(".chirp-modules")
BACKUP_DIR = Path("radio-backups")

#: Pause between writing a block command and reading its reply. Needed only
#: for counterfeit PL2303 cables, and harmless on a genuine one.
BLOCK_SETTLE_SECONDS = 0.05


def load_tdh9_module(path: Optional[Path] = None):
    """Import the TD-H9 test driver so it registers itself with CHIRP."""
    from chirp import directory

    directory.import_drivers()

    if path is None:
        candidates = sorted(MODULE_DIR.glob("tdh8_*.py"))
        if not candidates:
            raise SystemExit(
                "No TD-H9 driver module found. Run:\n"
                "  python scripts/radios/fetch_chirp_tdh9_module.py"
            )
        path = candidates[-1]

    spec = importlib.util.spec_from_file_location("tdh8_test_module", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load driver module {path}")
    module = importlib.util.module_from_spec(spec)
    # The test module replaces CHIRP's shipped tdh8 drivers rather than adding
    # to them, so their ids collide. This is the same hook CHIRP's own
    # "Load module from issue" uses to allow that.
    directory.enable_reregistrations()
    sys.modules["tdh8_test_module"] = module
    spec.loader.exec_module(module)
    print(f"Loaded TD-H9 driver module: {path}")
    return module


def find_radio_class(model_hint: str = "TD-H9"):
    from chirp import directory

    matches = {
        key: cls
        for key, cls in directory.DRV_TO_RADIO.items()
        if model_hint.lower().replace("-", "") in key.lower().replace("-", "").replace("_", "")
    }
    if not matches:
        raise SystemExit(
            f"No driver registered for {model_hint!r}. Available TIDRADIO drivers: "
            + ", ".join(k for k in directory.DRV_TO_RADIO if "tid" in k.lower())
        )
    return matches


def patch_slow_cable(module) -> None:
    """Make block *reads* tolerate a slow counterfeit PL2303 cable.

    The driver writes a command and immediately reads the reply. On a genuine
    cable that is fine. On a clone PL2303 the write can still be sitting in
    the chip's buffer when the read starts, so the reply never arrives inside
    the timeout and the transfer fails at the very first block - even though
    the handshake, which is more forgiving, succeeded.

    Flushing the write and pausing before the read fixes it. The framing here
    was confirmed by direct observation before being written down: ``R`` +
    u16be address + u8 size, answered by ``W`` + address + size + payload +
    checksum, 37 bytes for a 0x20 read.

    **The write path is deliberately left alone.** An earlier version of this
    function replaced ``_write_block`` too, and got it wrong in three ways:
    the payload is taken from ``mmap[addr + 8:addr + 40]`` because the eight
    ident bytes sit at the front of the map, the checksum covers only the
    payload, and the radio returns an acknowledgement that must be checked.
    The replacement skipped the acknowledgement, so a failed upload reported
    success and the radio kept its old channels. Reads are safe to adjust
    because a wrong read fails loudly; writes are not.
    """
    import struct

    from chirp import errors

    def _read_block(radio, start, size):
        pipe = radio.pipe
        cmd = struct.pack(">cHb", b"R", start, size)
        expected = b"W" + cmd[1:]

        pipe.write(cmd)
        pipe.flush()
        time.sleep(BLOCK_SETTLE_SECONDS)
        response = pipe.read(5 + size)

        if len(response) < 4 or response[:4] != expected:
            raise errors.RadioError(
                f"Error reading block {start:04x}: got {len(response)} bytes"
            )
        # The Bluetooth path omits the trailing checksum byte; accept both.
        if len(response) == 5 + size:
            return response[4:-1]
        if len(response) == 4 + size:
            return response[4:]
        raise errors.RadioError(
            f"Short read at {start:04x}: got {len(response)} bytes"
        )

    module._read_block = _read_block
    print(f"Patched block reads for a slow cable ({BLOCK_SETTLE_SECONDS}s settle)")


def download(port: str, radio_cls, label: str, attempts: int = 3) -> "object":
    import serial

    print(f"Reading {radio_cls.VENDOR} {radio_cls.MODEL} from {port} ...")
    print(f"  {radio_cls.BAUD_RATE} baud")

    last_error = None
    for attempt in range(1, attempts + 1):
        pipe = serial.Serial(port=port, baudrate=radio_cls.BAUD_RATE, timeout=2)
        try:
            # A counterfeit PL2303 needs a moment after the port opens before
            # it will carry the clone handshake reliably, and the radio can
            # be left mid-session by a previous attempt. Clearing both
            # directions and pausing costs nothing and avoids both.
            pipe.reset_input_buffer()
            pipe.reset_output_buffer()
            time.sleep(0.5)

            # The driver's download path assumes the radio has already been
            # put into clone mode by detect_from_serial(), which sends the
            # handshake and reads the model identity. Calling sync_in()
            # without it leaves the radio in normal operation, and every
            # block read comes back empty.
            detected = radio_cls.detect_from_serial(pipe)
            if detected is not radio_cls:
                print(f"  radio identifies as {detected.MODEL}")
            radio = detected(pipe)
            radio.status_fn = lambda status: None
            radio.sync_in()
            break
        except Exception as exc:  # noqa: BLE001 - retried below
            last_error = exc
            print(f"  attempt {attempt} failed: {exc}")
            if attempt < attempts:
                print("  retrying ...")
                time.sleep(2.0)
        finally:
            pipe.close()
    else:
        raise SystemExit(
            f"could not read the radio after {attempts} attempts: {last_error}\n"
            "Turn the radio off and on again, make sure the two-pin plug is "
            "pushed fully home, and try once more."
        )

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = BACKUP_DIR / f"{label}-{stamp}.img"
    radio.save_mmap(str(backup))
    size = backup.stat().st_size
    if size == 0:
        raise SystemExit(f"backup {backup} is empty; refusing to continue")
    print(f"  saved backup: {backup} ({size} bytes)")
    return radio, backup


def apply_csv(radio, csv_path: Path) -> int:
    from chirp.drivers import generic_csv

    source = generic_csv.CSVRadio(str(csv_path))
    memories = [m for m in source.get_memories() if not m.empty]
    features = radio.get_features()
    bounds = features.memory_bounds
    levels = list(features.valid_power_levels)
    print(f"Applying {len(memories)} channels from {csv_path}")
    print(f"  radio memory bounds: {bounds}")
    print(f"  power levels: {', '.join(f'{p} ({int(p)} dBm)' for p in levels)}")

    if memories and memories[-1].number > bounds[1]:
        raise SystemExit(
            f"CSV uses channel {memories[-1].number}, radio holds {bounds[1]}"
        )

    # Clear every slot the plan does not use, so a previous programming run
    # cannot leave orphan channels behind the new list.
    used = {m.number for m in memories}
    for number in range(bounds[0], bounds[1] + 1):
        if number in used:
            continue
        try:
            radio.erase_memory(number)
        except Exception:  # noqa: BLE001 - some slots are not erasable
            pass

    applied = 0
    for memory in memories:
        # The driver stores power as an index found with
        # ``self._tx_power.index(mem.power)``, which needs the radio's own
        # PowerLevel object. A level parsed from CSV is a different object,
        # so the lookup raises and the driver silently falls back to index 0
        # - every channel ends up on Low. Substituting the radio's own
        # nearest level keeps the requested power instead of losing it.
        if memory.power is not None and levels:
            memory.power = min(levels, key=lambda lv: abs(int(lv) - int(memory.power)))
        radio.set_memory(memory)
        applied += 1
    return applied


def upload(port: str, radio, attempts: int = 3) -> None:
    import serial

    print(f"Writing to radio on {port} ...")
    # Unlike the download path, the driver's upload sends its own handshake,
    # so the radio must be back in normal operation before this starts.
    last_error = None
    for attempt in range(1, attempts + 1):
        pipe = serial.Serial(port=port, baudrate=radio.BAUD_RATE, timeout=2)
        try:
            pipe.reset_input_buffer()
            pipe.reset_output_buffer()
            time.sleep(1.0)
            radio.set_pipe(pipe)
            radio.status_fn = lambda status: None
            radio.sync_out()
            print("  write complete")
            return
        except Exception as exc:  # noqa: BLE001 - retried below
            last_error = exc
            print(f"  attempt {attempt} failed: {exc}")
            if attempt < attempts:
                print("  retrying ...")
                time.sleep(3.0)
        finally:
            pipe.close()

    raise SystemExit(
        f"could not write to the radio after {attempts} attempts: {last_error}\n"
        "The radio is unchanged. Turn it off and on again and retry."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="Serial port, e.g. COM3")
    parser.add_argument("--csv", help="CHIRP Generic CSV to program")
    parser.add_argument("--module", help="Driver module path (default: newest fetched)")
    parser.add_argument("--label", default="td-h9", help="Backup filename prefix")
    parser.add_argument(
        "--backup-only", action="store_true", help="Read the radio and stop"
    )
    parser.add_argument(
        "--restore",
        help="Write a previously saved .img backup back to the radio "
        "(requires --execute)",
    )
    parser.add_argument(
        "--execute", action="store_true", help="Actually write to the radio"
    )
    parser.add_argument("--list-drivers", action="store_true")
    args = parser.parse_args(argv)

    module = load_tdh9_module(Path(args.module) if args.module else None)
    patch_slow_cable(module)
    matches = find_radio_class()
    if args.list_drivers:
        for key in sorted(matches):
            print(key)
        return 0

    # Prefer the plain TD-H9 driver over its HAM/GMRS subclasses; the radio
    # reports its own mode during the handshake.
    key = sorted(matches, key=lambda k: (len(k), k))[0]
    radio_cls = matches[key]
    print(f"Using driver: {key}")

    # Restoring is deliberately separate from the CSV path: the image is
    # already a complete radio memory, so it is uploaded as-is with no
    # channel staging. The current contents are still backed up first.
    if args.restore:
        image = Path(args.restore)
        if not image.is_file():
            raise SystemExit(f"backup image not found: {image}")
        _current, backup = download(args.port, radio_cls, f"{args.label}-pre-restore")
        print(f"\nRestoring from {image}")
        if not args.execute:
            print("DRY RUN. Nothing was written to the radio.")
            print(f"Current contents saved at {backup}")
            print("Re-run with --execute to restore.")
            return 0
        upload(args.port, radio_cls(str(image)))
        print(f"\nRestore complete. Previous contents saved at {backup}")
        print("Power-cycle the radio before reading it again.")
        return 0

    radio, backup = download(args.port, radio_cls, args.label)
    if args.backup_only or not args.csv:
        print("\nBackup only; radio not modified.")
        return 0

    applied = apply_csv(radio, Path(args.csv))
    print(f"  staged {applied} channels into the image")

    if not args.execute:
        print("\nDRY RUN. Nothing was written to the radio.")
        print(f"Backup saved at {backup}")
        print("Re-run with --execute to program the radio.")
        return 0

    upload(args.port, radio)

    print("\nVerifying by reading the radio back ...")
    print("  If this fails, power-cycle the radio and run with --backup-only.")
    verify, _ = download(args.port, radio_cls, f"{args.label}-verify")

    # CloneModeRadio has no get_memories(); walk the declared bounds instead.
    low, high = radio.get_features().memory_bounds
    mismatches = []
    checked = 0
    for number in range(low, high + 1):
        written = radio.get_memory(number)
        if written.empty:
            continue
        checked += 1
        read_back = verify.get_memory(number)
        if read_back.empty or read_back.freq != written.freq:
            mismatches.append(number)

    if mismatches:
        print(f"  MISMATCH in {len(mismatches)} channel(s): {mismatches[:10]}")
        print(f"  restore from {backup} if needed")
        return 1
    print(f"  verified {checked} channels read back correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
