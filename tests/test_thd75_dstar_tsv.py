"""The TH-D75 DR repeater list is written the way MCP-D75 imports it."""
from types import SimpleNamespace

from wasds150.export.thd75_dstar_tsv import HEADER, encode_dstar_tsv, render_dstar_tsv


def _dv(label, rx, tx, rpt1, lat=47.6172, lon=-122.2011):
    return SimpleNamespace(label=label, mode="DV", rx_freq_mhz=rx, tx_freq_mhz=tx, dv_rpt1=rpt1,
                           dv_rpt2=f"{rpt1[:7]}G", lat=lat, lon=lon)


def test_the_list_is_utf16_with_a_byte_order_mark_like_kenwoods_own():
    text = render_dstar_tsv([
        _dv("K7XYZ C - Bellevue", 146.4125, 147.4125, "K7XYZ  C"),
        _dv("K7XYZ C - Bellevue", 146.4125, 147.4125, "K7XYZ  C"),  # a second copy of the module
        _dv("W7NOP B - Nowhere", 443.0, 448.0, "W7NOP  B", lat=None, lon=None),  # no position: not listed
    ])
    data = encode_dstar_tsv(text)
    # MCP-D75 refuses an ASCII file as a list in another language.
    assert data[:2] == b"\xff\xfe"
    lines = data[2:].decode("utf-16-le").split("\r\n")
    assert lines[0].split("\t") == list(HEADER)
    row = lines[1].split("\t")
    assert len(row) == len(HEADER) and lines[2:] == [""]
    assert (row[6], row[7], row[9], row[11], row[12], row[13]) == ("K7XYZ  C", "K7XYZ  G", "Bellevue", "146.4125", "+", "1")
