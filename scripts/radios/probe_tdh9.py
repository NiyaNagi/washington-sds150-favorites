"""Diagnose the serial link to a TIDRADIO TD-H9.

The TD-H9's native USB-C serial is known to be unreliable - CHIRP's maintainer
reported that it "occasionally enumerates and binds, but most of the time
not", and recommends the Kenwood K1 two-pin CH340 cable instead.  When a
download fails it is worth knowing whether the radio answered the handshake
at all before blaming the channel plan.

This only reads. It never writes to the radio.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from program_tdh9 import load_tdh9_module  # noqa: E402

MAGIC = b"PVOJH\x5c\x14"


def probe(port: str, baud: int, attempts: int) -> int:
    import serial

    for attempt in range(1, attempts + 1):
        print(f"\n--- attempt {attempt} at {baud} baud on {port} ---")
        try:
            pipe = serial.Serial(port=port, baudrate=baud, timeout=2, write_timeout=2)
        except Exception as exc:  # noqa: BLE001
            print(f"  cannot open port: {exc}")
            return 1
        try:
            pipe.reset_input_buffer()
            pipe.reset_output_buffer()
            pipe.write(MAGIC)
            pipe.flush()
            time.sleep(0.2)
            ack = pipe.read(1)
            print(f"  handshake ack: {ack!r}")
            if not ack:
                print("  no response - radio off, wrong port, or link not up")
                continue

            pipe.write(b"\x02")
            pipe.flush()
            time.sleep(0.2)
            ident = pipe.read(8)
            print(f"  ident bytes:   {ident!r}")
            if len(ident) == 8:
                model = ident[:4].decode("ascii", "replace")
                mode_byte = ident[7:8]
                modes = {b"N": "Normal", b"H": "HAM", b"G": "GMRS"}
                print(f"  model:         {model}")
                print(f"  mode:          {modes.get(mode_byte, repr(mode_byte))}")

            pipe.write(b"\x06")
            pipe.flush()
            time.sleep(0.1)
            print(f"  ack to ident:  {pipe.read(1)!r}")

            # One 8-byte block read from address 0.
            pipe.write(b"R" + (0).to_bytes(2, "big") + bytes([8]))
            pipe.flush()
            time.sleep(0.2)
            block = pipe.read(4 + 8 + 1)
            print(f"  block read:    {block!r} ({len(block)} bytes)")
            if len(block) >= 12:
                print("  LINK OK")
                return 0
            print("  block read short - this is the failure mode CHIRP reports")
        finally:
            pipe.close()
    return 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--drivers", action="store_true", help="List drivers and exit")
    args = parser.parse_args(argv)

    if args.drivers:
        from chirp import directory

        load_tdh9_module()
        for key in sorted(directory.DRV_TO_RADIO):
            if "TD-H9" in key:
                print(key)
        return 0

    return probe(args.port, args.baud, args.attempts)


if __name__ == "__main__":
    sys.exit(main())
