"""The TH-D75 DR repeater list is written the way MCP-D75 imports it, and
keeps the entries already on the radio."""
import struct
from types import SimpleNamespace

from wasds150.export.thd75_dstar_tsv import HEADER, LIST_START, encode_dstar_tsv, read_repeater_list, render_dstar_tsv


def _dv(label, rx, tx, rpt1, lat=47.6172, lon=-122.2011):
    return SimpleNamespace(label=label, mode="DV", rx_freq_mhz=rx, tx_freq_mhz=tx, dv_rpt1=rpt1,
                           dv_rpt2=f"{rpt1[:7]}G", lat=lat, lon=lon)


def _record(name, rpt1, freq_hz, offset_hz, shift, lat, lon, flags=0xE8, group=(3, 50, 156)):
    record = bytearray(b"\xff" * 0x50)
    record[0x00:0x10] = name.encode().ljust(16, b"\x00")
    record[0x10:0x20] = b"Washington".ljust(16, b"\x00")
    record[0x20:0x28] = rpt1.encode()
    record[0x28:0x30] = (rpt1[:7] + "G").encode()
    struct.pack_into("<II", record, 0x30, freq_hz, offset_hz)
    struct.pack_into("<BBHBBH", record, 0x38, *lat, *lon)
    record[0x40:0x46] = bytes((0xFB, 0x01, 0x18, shift, 0xFF, 0xFF))
    record[0x46:0x49] = bytes(group)
    record[0x4B] = flags
    return bytes(record)


def _image(*records):
    image = bytearray(b"\xff" * (0x100 + LIST_START + 0x400))
    for index, record in enumerate(records):
        page, within = divmod(index, 3)
        start = 0x100 + LIST_START + page * 0x100 + within * 0x50
        image[start:start + 0x50] = record
    return bytes(image)


def test_the_radios_list_is_read_back_from_its_file():
    image = _image(
        _record("Federal Way", "K7AAA  C", 146_840_000, 600_000, 1, (47, 18, 3400), (122, 19, 3700), flags=0xEE),
        _record("Bellevue", "K7XYZ  C", 146_125_000, 1_000_000, 2, (47, 36, 9900), (122, 12, 1000)),
        _record("Vancouver", "VE7ZZZ B", 442_000_000, 5_000_000, 2, (49, 15, 0), (123, 6, 0), group=(3, 49, 1)),
    )
    rows = read_repeater_list(image)
    # A group without Kenwood names here (British Columbia) is skipped, not guessed.
    assert [row[6] for row in rows] == ["K7AAA  C", "K7XYZ  C"]
    federal = rows[0]
    assert len(federal) == len(HEADER)
    assert (federal[9], federal[11], federal[12], federal[13]) == ("Federal Way", "146.8400", "-", "0.6")
    assert (federal[18], federal[19], federal[21], federal[22]) == ("47", "18.34", "122", "19.37")
    assert (federal[26], federal[27]) == ("On", "On")


def test_the_list_merges_the_radios_entries_and_is_utf16_like_kenwoods_own():
    existing = read_repeater_list(_image(
        _record("Federal Way", "K7AAA  C", 146_840_000, 600_000, 1, (47, 18, 3400), (122, 19, 3700)),
        _record("Bellevue", "K7XYZ  C", 146_125_000, 1_000_000, 2, (47, 36, 9900), (122, 12, 1000)),
    ))
    text = render_dstar_tsv([
        _dv("K7XYZ C - Bellevue", 146.4125, 147.4125, "K7XYZ  C"),
        _dv("K7XYZ C - Bellevue", 146.4125, 147.4125, "K7XYZ  C"),  # a second copy of the module
        _dv("W7NOP B - Nowhere", 443.0, 448.0, "W7NOP  B", lat=None, lon=None),  # no position: not listed
    ], existing)
    data = encode_dstar_tsv(text)
    # MCP-D75 refuses an ASCII file as a list in another language.
    assert data[:2] == b"\xff\xfe"
    lines = data[2:].decode("utf-16-le").split("\r\n")
    assert lines[0].split("\t") == list(HEADER) and lines[-1] == ""
    rows = [line.split("\t") for line in lines[1:-1]]
    assert all(len(row) == len(HEADER) for row in rows)
    # The plan's record of a repeater replaces the radio's (146.125 -> 146.4125); the radio's others stay.
    assert [(row[6], row[9], row[11]) for row in rows] == [
        ("K7XYZ  C", "Bellevue", "146.4125"), ("K7AAA  C", "Federal Way", "146.8400"),
    ]
