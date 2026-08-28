"""Sort TH-D75 repeater memories and add the audited WW7MST gaps.

Only ordinary-memory flags, records, and names are changed. Every menu,
APRS/GPS/D-STAR-list, bitmap, special-memory, and unknown byte is preserved
from the supplied MCP-D75 image.
"""
from __future__ import annotations

import argparse
import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path

from wasds150.export.thd75_target import (
    DATA_OFFSET,
    DSTAR_REGION_END,
    DSTAR_REGION_START,
    FILE_SIZE,
    FLAG_SIZE,
    FLAGS_OFFSET,
    HEADER_SIZE,
    MEMORY_COUNT,
    NAME_SIZE,
    NAMES_OFFSET,
    PAGE_SIZE,
    RECORD_SIZE,
    Thd75ExportResult,
    _name_bytes,
    _record,
    inspect_thd75,
)
from wasds150.plan.resolve import PlannedChannel
from wasds150.radios.tones import parse_tone

REPEATER_GROUPS = frozenset({0, 1, 2, 3})

# name, receive MHz, transmit MHz, physical group
AUDITED_ADDITIONS = (
    ("WW7MSTSEATTLE", 146.900, 146.300, 0),
    ("WW7MSTSEATTLE", 224.680, 223.080, 1),
    ("WW7MSTSEATTLE", 443.550, 448.550, 2),
    ("WW7MSTTACOMA", 443.675, 448.675, 2),
    # 444.825 / 449.825 is already present in the supplied image.
)


@dataclass(frozen=True)
class RawMemory:
    original_slot: int
    flag: bytes
    record: bytes
    name: bytes

    @property
    def group(self) -> int:
        return self.flag[2]

    @property
    def rx_hz(self) -> int:
        return struct.unpack_from("<I", self.record, 0)[0]

    @property
    def mode(self) -> int:
        return self.record[0x09] >> 4

    @property
    def text_name(self) -> str:
        return self.name.split(b"\x00", 1)[0].decode("ascii", "replace").rstrip()

    @property
    def tx_hz(self) -> int:
        value = struct.unpack_from("<I", self.record, 4)[0]
        shift = self.record[0x0A] & 0x03
        if self.record[0x0A] & 0x04:
            return value
        if shift == 1:
            return self.rx_hz + value
        if shift == 2:
            return self.rx_hz - value
        return self.rx_hz


def _data_offset(slot: int) -> int:
    page, within = divmod(slot, 6)
    return HEADER_SIZE + DATA_OFFSET + page * PAGE_SIZE + within * RECORD_SIZE


def _flag_offset(slot: int) -> int:
    return HEADER_SIZE + FLAGS_OFFSET + slot * FLAG_SIZE


def _name_offset(slot: int) -> int:
    return HEADER_SIZE + NAMES_OFFSET + slot * NAME_SIZE


def _read_memories(data: bytes) -> list[RawMemory]:
    memories = []
    for slot in range(MEMORY_COUNT):
        flag_start = _flag_offset(slot)
        flag = data[flag_start:flag_start + FLAG_SIZE]
        if flag[0] == 0xFF:
            continue
        record_start = _data_offset(slot)
        name_start = _name_offset(slot)
        memories.append(
            RawMemory(
                original_slot=slot,
                flag=flag,
                record=data[record_start:record_start + RECORD_SIZE],
                name=data[name_start:name_start + NAME_SIZE],
            )
        )
    return memories


def _new_memory(name: str, rx_mhz: float, tx_mhz: float, group: int) -> RawMemory:
    channel = PlannedChannel(
        slot=0,
        name=name,
        label=name,
        rx_freq_mhz=rx_mhz,
        tx_freq_mhz=tx_mhz,
        transmit=True,
        mode="FM",
        block={0: "2m Repeaters", 1: "1.25m Repeaters", 2: "70cm Repeaters"}[group],
        source="THD75WWARA/2026-08-27",
        tx_tone=parse_tone("TONE=C103.5"),
        power="5.0W",
    )
    result = Thd75ExportResult()
    record = _record(channel, result)
    if result.warnings:
        raise RuntimeError("unexpected warning while encoding audited repeater")
    return RawMemory(
        original_slot=MEMORY_COUNT,
        flag=bytes((group, 0, group, 0xFF)),
        record=record,
        name=_name_bytes(name),
    )


def _tuning_key(memory: RawMemory) -> tuple[int, int, int]:
    return memory.rx_hz, memory.tx_hz, memory.mode


def _write_memory(output: bytearray, slot: int, memory: RawMemory) -> None:
    flag_start = _flag_offset(slot)
    data_start = _data_offset(slot)
    name_start = _name_offset(slot)
    output[flag_start:flag_start + FLAG_SIZE] = memory.flag
    output[data_start:data_start + RECORD_SIZE] = memory.record
    output[name_start:name_start + NAME_SIZE] = memory.name


def _owned(index: int, last_slot: int) -> bool:
    if _flag_offset(0) <= index < _flag_offset(last_slot) + FLAG_SIZE:
        return True
    if _name_offset(0) <= index < _name_offset(last_slot) + NAME_SIZE:
        return True
    relative = index - (HEADER_SIZE + DATA_OFFSET)
    if relative < 0:
        return False
    page, within = divmod(relative, PAGE_SIZE)
    if within >= 6 * RECORD_SIZE:
        return False
    slot = page * 6 + within // RECORD_SIZE
    return slot <= last_slot


def update(data: bytes, dstar_source: bytes | None = None) -> tuple[bytes, list[RawMemory]]:
    if len(data) != FILE_SIZE or not data.startswith(b"MCP-D75\xFFV1."):
        raise ValueError("input is not an exact-size MCP-D75 file")
    existing = _read_memories(data)
    repeaters = [memory for memory in existing if memory.group in REPEATER_GROUPS]
    other = [memory for memory in existing if memory.group not in REPEATER_GROUPS]
    keys = {_tuning_key(memory) for memory in repeaters}
    added = []
    for spec in AUDITED_ADDITIONS:
        memory = _new_memory(*spec)
        if _tuning_key(memory) not in keys:
            repeaters.append(memory)
            added.append(memory)
            keys.add(_tuning_key(memory))

    repeaters.sort(key=lambda memory: (memory.group, memory.rx_hz, memory.text_name.upper()))
    ordered = repeaters + other
    if len(ordered) > MEMORY_COUNT:
        raise ValueError(f"updated image needs {len(ordered)} memories; capacity is {MEMORY_COUNT}")

    output = bytearray(data)
    if dstar_source is not None:
        if len(dstar_source) != FILE_SIZE:
            raise ValueError("D-STAR source is not an exact-size MCP-D75 file")
        start = HEADER_SIZE + DSTAR_REGION_START
        end = HEADER_SIZE + DSTAR_REGION_END
        output[start:end] = dstar_source[start:end]
    for slot, memory in enumerate(ordered):
        _write_memory(output, slot, memory)

    # The input is contiguous, and this operation only adds channels, so no
    # trailing formerly-used records need clearing.
    if len(ordered) < len(existing):
        raise AssertionError("updater unexpectedly removed memory channels")

    for index, (before, after) in enumerate(zip(data, output)):
        in_dstar = (
            dstar_source is not None
            and HEADER_SIZE + DSTAR_REGION_START <= index < HEADER_SIZE + DSTAR_REGION_END
        )
        if before != after and not (_owned(index, len(ordered) - 1) or in_dstar):
            raise AssertionError(f"changed non-memory byte at file offset 0x{index:X}")
    return bytes(output), added


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--dstar-source",
        type=Path,
        help="Optional MCP-D75 image supplying the native D-STAR repeater region",
    )
    args = parser.parse_args()

    original = args.input.read_bytes()
    dstar_source = args.dstar_source.read_bytes() if args.dstar_source else None
    updated, added = update(original, dstar_source=dstar_source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(updated)

    rows = inspect_thd75(updated)
    print(f"input memories: {len(inspect_thd75(original))}")
    print(f"output memories: {len(rows)}")
    print(f"added: {len(added)}")
    for memory in added:
        print(
            f"  {memory.text_name}: {memory.rx_hz / 1_000_000:.6f} -> "
            f"{memory.tx_hz / 1_000_000:.6f} MHz, group {memory.group}"
        )
    print(f"SHA-256 {hashlib.sha256(updated).hexdigest().upper()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
