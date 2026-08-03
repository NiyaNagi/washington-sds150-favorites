"""Tests for the generic, reusable free-text channel parser (see module
docstring for the non-fabrication discipline this locks in)."""
from __future__ import annotations

from wasds150.sources.static_channels import parse_department_text


def test_single_explicit_frequency():
    result = parse_department_text("Ch16 156.800(distress)")
    assert len(result.channels) == 1
    ch = result.channels[0]
    assert ch.label == "Ch16"
    assert ch.freq_mhz == 156.8
    assert ch.note == "distress"
    assert result.skipped_ranges == []


def test_frequency_glued_directly_to_label_with_no_space():
    result = parse_department_text("KXI27 Forks162.425")
    assert len(result.channels) == 1
    assert result.channels[0].label == "KXI27 Forks"
    assert result.channels[0].freq_mhz == 162.425


def test_semicolon_separated_segments():
    result = parse_department_text("CMD 46.520; RADEF 46.000")
    freqs = {c.label: c.freq_mhz for c in result.channels}
    assert freqs == {"CMD": 46.52, "RADEF": 46.0}


def test_comma_separated_pieces_within_one_segment():
    result = parse_department_text("KSEA Tower119.9,ATIS118.0,Ground121.7")
    freqs = {c.label: c.freq_mhz for c in result.channels}
    assert freqs == {"KSEA Tower": 119.9, "ATIS": 118.0, "Ground": 121.7}


def test_comma_inside_parentheses_does_not_split_the_piece():
    result = parse_department_text("District dispatch (D1 Pierce,D2 King)")
    # No explicit frequency anywhere in this text -- nothing should convert,
    # and the comma-in-parens must not have produced a spurious extra piece.
    assert result.channels == []
    assert result.skipped_ranges == []


def test_slash_joined_explicit_list_becomes_multiple_channels():
    result = parse_department_text("SAR1-5 155.160/155.2425/155.3025/155.1675/155.1825")
    assert [c.freq_mhz for c in result.channels] == [155.160, 155.2425, 155.3025, 155.1675, 155.1825]
    # The label's own numeric range ("1-5") is used to derive precise
    # per-channel labels rather than a generic "(n)" suffix.
    assert [c.label for c in result.channels] == ["SAR1", "SAR2", "SAR3", "SAR4", "SAR5"]


def test_slash_joined_list_with_bare_integer_pattern_in_label():
    result = parse_department_text("CEMNET-1/2/3 45.200/45.360/45.480 (PL 127.3)")
    assert [c.label for c in result.channels] == ["CEMNET-1", "CEMNET-2", "CEMNET-3"]
    assert [c.freq_mhz for c in result.channels] == [45.2, 45.36, 45.48]
    assert all(c.tone == "CTCSS 127.3" for c in result.channels)


def test_slash_joined_list_without_a_recognizable_index_pattern_uses_generic_suffix():
    result = parse_department_text("Odessa PD158.730/158.940")
    assert [c.label for c in result.channels] == ["Odessa PD", "Odessa PD (2)"]
    assert [c.freq_mhz for c in result.channels] == [158.73, 158.94]


def test_hyphen_joined_range_is_never_expanded():
    result = parse_department_text("ITAC1-4 866.5125-868.0125")
    assert result.channels == []
    assert result.skipped_ranges == ["866.5125-868.0125"]


def test_range_and_explicit_frequency_in_same_text_only_skips_the_range():
    result = parse_department_text("ICALL 866.0125; ITAC1-4 866.5125-868.0125")
    assert len(result.channels) == 1
    assert result.channels[0].label == "ICALL"
    assert result.channels[0].freq_mhz == 866.0125
    assert result.skipped_ranges == ["866.5125-868.0125"]


def test_tone_extraction_removes_tone_from_frequency_scan():
    result = parse_department_text("DNR Common 151.415 (PL103.5); regional repeater")
    assert len(result.channels) == 1
    assert result.channels[0].freq_mhz == 151.415
    assert result.channels[0].tone == "CTCSS 103.5"


def test_dcs_tone_extraction():
    result = parse_department_text("SAR154.1075(DCS-565)")
    assert len(result.channels) == 1
    assert result.channels[0].tone == "DCS 565"


def test_wattage_rating_is_never_mistaken_for_a_frequency():
    # A real regression: "(0.5W)" must never produce a bogus 0.5 MHz
    # channel. The whole segment is a range anyway (skipped), but the
    # guard is general (see module docstring).
    result = parse_department_text("Ch8-14 FRS-only467.5625-467.7125(0.5W)")
    assert result.channels == []
    for ch in result.channels:
        assert ch.freq_mhz != 0.5


def test_band_nickname_is_never_mistaken_for_a_frequency():
    # A real regression: "(1.25m national)" must never also produce a
    # bogus 1.25 MHz channel alongside the real 223.500 one.
    result = parse_department_text("223.500(1.25m national)")
    assert len(result.channels) == 1
    assert result.channels[0].freq_mhz == 223.5


def test_no_frequency_present_produces_nothing():
    result = parse_department_text("District dispatch (D1 Pierce,D2 King,D4 Spokane/SE); tactical/car-to-car")
    assert result.channels == []
    assert result.skipped_ranges == []


def test_trunked_talkgroup_mention_without_frequency_is_never_fabricated():
    result = parse_department_text("USCG P25 NAC293 nets")
    assert result.channels == []


def test_empty_text_returns_empty_result():
    result = parse_department_text("")
    assert result.channels == []
    assert result.skipped_ranges == []


def test_every_emitted_frequency_is_plausible_and_literal():
    """Regression-style sweep: for a batch of varied real-shaped inputs,
    every emitted frequency must be a value that was literally present in
    the source text (never interpolated) and within a plausible scanner
    range."""
    samples = [
        "MURS Ch1-3 151.820/151.880/151.940(light)",
        "Ch4 Blue Dot154.570(heavy)",
        "WSDOT V1/V2/V3 151.070/151.025/156.120",
        "KGEG ATIS124.325,Tower118.3,Approach123.75/133.35(shared Fairchild)",
        "Guard121.5/243.0(UHF)",
        "NWAC/SPART FRS Ch7 462.7125(CTCSS71.9,legal transmit)",
    ]
    for text in samples:
        result = parse_department_text(text)
        for ch in result.channels:
            assert 1.0 <= ch.freq_mhz <= 1300.0
            assert f"{ch.freq_mhz:g}" in text or f"{ch.freq_mhz:.3f}" in text or f"{ch.freq_mhz:.4f}" in text
