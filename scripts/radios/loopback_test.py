"""Check a serial cable's wiring without needing a radio attached.

A programming cable that opens but never answers has three common causes,
and they are worth telling apart before blaming the radio:

* the plug is not fully seated - the Kenwood two-pin connector needs a much
  firmer push than feels reasonable, and a partial insertion gives exactly
  this symptom;
* the cable's TX and RX are not looped by the radio, so nothing echoes;
* the chip is dead.

With the plug **out of the radio**, briefly bridging the tip of the speaker
plug to the tip of the microphone plug ties TX to RX. Anything written should
then come straight back. That separates a cable fault from a radio fault.
"""
from __future__ import annotations

import argparse
import sys
import time

TEST_PATTERN = b"WASDS150-LOOPBACK-TEST"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args(argv)

    import serial

    print(f"Opening {args.port} at {args.baud} baud ...")
    try:
        pipe = serial.Serial(port=args.port, baudrate=args.baud, timeout=2)
    except Exception as exc:  # noqa: BLE001
        print(f"  cannot open: {exc}")
        return 1

    try:
        print("  port opened")
        print()
        print("Modem status lines (these come from the chip itself):")
        for name in ("cts", "dsr", "ri", "cd"):
            try:
                print(f"  {name.upper():<4} {getattr(pipe, name)}")
            except Exception as exc:  # noqa: BLE001
                print(f"  {name.upper():<4} unavailable ({exc})")

        print()
        print("Writing a test pattern. With the plugs bridged you should see it")
        print("come back; with nothing bridged, silence is expected.")
        pipe.reset_input_buffer()
        pipe.reset_output_buffer()
        pipe.write(TEST_PATTERN)
        pipe.flush()
        time.sleep(0.4)
        echoed = pipe.read(len(TEST_PATTERN))
        print(f"  wrote    {TEST_PATTERN!r}")
        print(f"  read     {echoed!r}")

        if echoed == TEST_PATTERN:
            print("\n  LOOPBACK OK - the cable's transmit and receive both work.")
            print("  If the radio still does not answer, the fault is the plug")
            print("  seating or the radio, not the cable.")
        elif echoed:
            print("\n  PARTIAL echo - the cable works but is dropping data.")
        else:
            print("\n  No echo. If the plugs were bridged, the cable is faulty.")
            print("  If they were not, this is the expected result.")
    finally:
        pipe.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
