"""Tests for the native ``.FTX1`` export target.

These run against the blank structural template that ships in the repository,
so they exercise the real write path without needing a file from the vendor
programmer.
"""
from __future__ import annotations

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.export.ftx1_file import (
    HOME_COUNT,
    HOME_FIRST,
    PMS_PAIRS,
    RECORD_COUNT,
    Ftx1File,
)
from wasds150.export.ftx1_target import (
    Ftx1ExportError,
    MEMORY_CAPACITY,
    NAME_LEN,
    render_ftx1,
    template_path,
    write_ftx1,
)
from wasds150.plan.service import resolve_named_plan


@pytest.fixture()
def ctx(tmp_path, repo_csv_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=repo_csv_path)


@pytest.fixture()
def resolved(ctx):
    _plan, resolved = resolve_named_plan(ctx, "ftx1-wa")
    return resolved


def _template_or_skip():
    path = template_path()
    if not path.is_file():
        pytest.skip(f"blank FTX-1 template not present at {path}")
    return path


# -------------------------------------------------------------- template --
def test_template_ships_with_the_repository():
    path = _template_or_skip()
    assert path.stat().st_size > 0


def test_template_carries_no_channel_data():
    """The template is structure only. If this fails, we are shipping someone
    else's channel list."""
    path = _template_or_skip()
    ftx1 = Ftx1File.load(path)
    populated = [record for record in ftx1.memories() if not record.empty]
    assert populated == []
    for record in ftx1.records:
        assert not record.name.strip()
        assert not record.comment.strip()


def test_template_round_trips():
    path = _template_or_skip()
    original = path.read_bytes()
    assert Ftx1File.load(path).round_trips(original)


# ---------------------------------------------------------------- render --
def test_render_writes_every_resolved_channel(resolved):
    _template_or_skip()
    ftx1, result = render_ftx1(resolved)
    assert result.rows == len(resolved.channels)
    populated = [r for r in ftx1.memories() if not r.empty]
    assert len(populated) == result.rows


def test_render_programs_scan_pairs(resolved):
    _template_or_skip()
    ftx1, result = render_ftx1(resolved)
    assert result.scan_pairs > 0
    assert result.scan_pairs <= PMS_PAIRS
    used = [pair for pair in ftx1.scan_limits() if not pair[0].empty]
    assert len(used) == result.scan_pairs
    for low, high in used:
        assert low.rx_hz < high.rx_hz, "a scan pair must span upwards"


def test_scan_pairs_do_not_consume_memories(resolved):
    """Scan limits live in their own region, so they cost no channel slots."""
    _template_or_skip()
    ftx1, result = render_ftx1(resolved)
    assert len(ftx1.memories()) == MEMORY_CAPACITY
    assert result.rows <= MEMORY_CAPACITY


def test_render_preserves_frequencies(resolved):
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    memories = [r for r in ftx1.memories() if not r.empty]
    for planned, record in zip(resolved.channels, memories):
        assert abs(record.rx_mhz - planned.rx_freq_mhz) < 1e-6


def test_names_are_truncated_to_the_display_width(resolved):
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    for record in ftx1.memories():
        assert len(record.name) <= NAME_LEN


def test_repeater_shift_is_written_for_transmit_channels(resolved):
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    memories = [r for r in ftx1.memories() if not r.empty]
    pairs = [
        (planned, record)
        for planned, record in zip(resolved.channels, memories)
        if planned.transmit
        and planned.tx_freq_mhz
        and abs(planned.tx_freq_mhz - planned.rx_freq_mhz) > 1e-6
    ]
    assert pairs, "expected at least one repeater channel in the plan"
    for planned, record in pairs:
        assert abs(record.tx_mhz - planned.tx_freq_mhz) < 1e-6


def test_receive_only_channels_get_no_shift(resolved):
    """A receive-only memory must not carry a transmit offset."""
    _template_or_skip()
    ftx1, _result = render_ftx1(resolved)
    memories = [r for r in ftx1.memories() if not r.empty]
    for planned, record in zip(resolved.channels, memories):
        if not planned.transmit:
            assert record.tx_hz == record.rx_hz


def test_missing_template_raises_a_useful_error(resolved, tmp_path):
    with pytest.raises(Ftx1ExportError, match="template not found"):
        render_ftx1(resolved, template=tmp_path / "absent.FTX1")


# ----------------------------------------------------------------- write --
def test_write_produces_a_loadable_file(resolved, tmp_path):
    _template_or_skip()
    out = tmp_path / "plan.FTX1"
    result = write_ftx1(resolved, out)
    assert out.is_file()

    reloaded = Ftx1File.load(out)
    populated = [r for r in reloaded.memories() if not r.empty]
    assert len(populated) == result.rows


def test_written_file_keeps_the_container_size(resolved, tmp_path):
    """The format is fixed-size; a size change means the record model is wrong."""
    template = _template_or_skip()
    out = tmp_path / "plan.FTX1"
    write_ftx1(resolved, out)
    assert out.stat().st_size == template.stat().st_size


def test_written_file_round_trips(resolved, tmp_path):
    _template_or_skip()
    out = tmp_path / "plan.FTX1"
    write_ftx1(resolved, out)
    assert Ftx1File.load(out).round_trips(out.read_bytes())


def test_export_registry_serves_the_right_radio():
    from wasds150.export.registry import get_target

    target = get_target("ftx1-file")
    assert target.radio_id == "ftx1"
    assert target.extension == ".FTX1"
    assert target.available is True


def test_ftx1_target_refuses_a_plan_for_another_radio(ctx):
    from wasds150.export.registry import get_target

    _plan, tdh9 = resolve_named_plan(ctx, "h9-ozette")
    with pytest.raises(ValueError):
        get_target("ftx1-file").check_radio(tdh9)


# ------------------------------------------------- settings preservation --
# A .FTX1 holds far more than channels: CW messages, GPS setup, display data
# and the HOME channels all live past the memory array. An earlier version of
# the format model divided the whole file by the record size, minting ~800
# phantom records out of that configuration area; the template builder then
# "cleared every record" and silently wiped the radio's settings. The file
# still loaded, and the memories were still correct, so nothing looked wrong.
class TestSettingsAreaPreserved:
    def test_record_array_is_bounded(self):
        """load() must not turn the configuration area into records."""
        assert RECORD_COUNT == HOME_FIRST + HOME_COUNT
        template = _template_or_skip()
        parsed = Ftx1File.load(template)
        assert len(parsed.records) == RECORD_COUNT
        # Everything past the array survives as an opaque trailer.
        assert len(parsed.trailer) > 0

    def test_template_keeps_settings_and_home(self):
        """The vendored template must be blank in memories but not elsewhere."""
        template = _template_or_skip()
        parsed = Ftx1File.load(template)

        # Only the handful of base records the exporter patches from remain...
        populated = [r for r in parsed.records[:MEMORY_CAPACITY] if not r.empty]
        assert len(populated) <= 3
        # ...but the radio's configuration is still there.
        assert sum(1 for b in parsed.trailer if b) > 1000, (
            "template lost its settings area; regenerate it with "
            "scripts/radios/make_ftx1_template.py"
        )
        home = b"".join(r.raw for r in parsed.records[HOME_FIRST:HOME_FIRST + HOME_COUNT])
        assert sum(1 for b in home if b) > 0, "template lost its HOME channels"

    def test_export_leaves_settings_byte_identical(self, resolved):
        """Exporting must change memories and scan limits, nothing else."""
        template = _template_or_skip()
        rendered, _result = render_ftx1(resolved)
        base = Ftx1File.load(template)

        assert rendered.trailer == base.trailer, "export modified radio settings"
        assert rendered.header == base.header, "export modified the header"
        for index in range(HOME_FIRST, HOME_FIRST + HOME_COUNT):
            assert rendered.records[index].raw == base.records[index].raw, (
                f"export modified HOME channel at record {index}"
            )


# --------------------------------------------------------- operating mode --
# Decoded by writing one memory per mode in the RT Systems programmer and
# diffing: all 18 rows were identical except the byte at 0x0E. Before this,
# every channel inherited the base record's mode, so a file built from the
# factory default (a 7 MHz HF memory) programmed 162 MHz weather as LSB.
class TestOperatingMode:
    def test_mode_codes_match_the_decoded_table(self):
        from wasds150.export import ftx1_file as F

        assert F.MODE_FM == 0x00
        assert F.MODE_AM == 0x01
        assert F.MODE_FM_NARROW == 0x03
        assert F.MODE_LSB == 0x05
        assert F.MODE_USB == 0x06
        assert F.MODE_CW_U == 0x18
        assert F.MODE_DN == 0x1C

    def test_patched_writes_the_mode_byte(self):
        from wasds150.export.ftx1_file import MODE_CODES, OFF_MODE

        template = _template_or_skip()
        record = Ftx1File.load(template).records[0]
        for name, code in MODE_CODES.items():
            assert record.patched(mode=name).raw[OFF_MODE] == code

    def test_unknown_mode_is_rejected(self):
        template = _template_or_skip()
        record = Ftx1File.load(template).records[0]
        with pytest.raises(ValueError, match="not a mode"):
            record.patched(mode="P25")

    def test_patched_writes_the_skip_flag(self):
        from wasds150.export.ftx1_file import OFF_SKIP

        template = _template_or_skip()
        record = Ftx1File.load(template).records[0]
        assert record.patched(skip=True).raw[OFF_SKIP] == 1
        assert record.patched(skip=False).raw[OFF_SKIP] == 0

    def test_export_sets_mode_per_band(self, resolved):
        """Airband must be AM and VHF/UHF must be FM, not the base's mode."""
        from wasds150.export.ftx1_file import MODE_AM, MODE_FM, OFF_MODE

        _template_or_skip()
        rendered, _result = render_ftx1(resolved)
        records = [r for r in rendered.records[:MEMORY_CAPACITY] if not r.empty]

        air = [r for r in records if 108e6 <= r.rx_hz <= 137e6]
        assert air, "expected airband channels in the shipped plan"
        assert all(r.raw[OFF_MODE] == MODE_AM for r in air)

        weather = [r for r in records if 162e6 <= r.rx_hz <= 163e6]
        assert weather, "expected NOAA weather channels in the shipped plan"
        assert all(r.raw[OFF_MODE] == MODE_FM for r in weather)

    def test_export_marks_data_channels_skip_scan(self, resolved):
        """Winlink and APRS are programmed but must not stop a scan."""
        from wasds150.export.ftx1_file import OFF_SKIP

        _template_or_skip()
        rendered, _result = render_ftx1(resolved)
        records = [r for r in rendered.records[:MEMORY_CAPACITY] if not r.empty]
        skipped = [r for r in records if r.raw[OFF_SKIP]]
        assert skipped, "expected at least one skip-scan channel"

    def test_offset_field_matches_the_shift(self, resolved):
        """The shift has its own field and its own column in the programmer."""
        import struct

        from wasds150.export.ftx1_file import OFF_OFFSET

        _template_or_skip()
        rendered, _result = render_ftx1(resolved)
        records = [r for r in rendered.records[:MEMORY_CAPACITY] if not r.empty]
        for record in records:
            stored = struct.unpack_from("<I", record.raw, OFF_OFFSET)[0]
            assert stored == abs(record.tx_hz - record.rx_hz)


# ------------------------------------------------------------- tone mode --
# Decoded by probe: 0 None, 1 Tone, 2 Tone Sql, 3 DCS, 8 Rev Tone.
# This project had 1 and 2 the wrong way round and wrote Tone Sql on every
# toned channel. That transmits the access tone correctly, so a repeater keys
# up - but it also mutes the receiver unless a matching tone comes back, and
# many repeaters do not send one. The channel then appears dead while looking
# perfectly programmed in the memory list.
class TestToneMode:
    def test_tone_mode_constants(self):
        from wasds150.export import ftx1_file as F

        assert F.TONE_OFF == 0
        assert F.TONE_CTCSS_ENC == 1, "Tone (encode only) is 1"
        assert F.TONE_CTCSS_ENC_DEC == 2, "Tone Sql (encode + decode) is 2"
        assert F.TONE_DCS == 3

    def test_a_tone_encodes_without_squelching(self):
        """Setting a tone must not mute the receiver."""
        from wasds150.export.ftx1_file import (
            OFF_TONE_MODE,
            OFF_TX_TONE,
            TONE_CTCSS_ENC,
        )

        template = _template_or_skip()
        record = Ftx1File.load(template).records[0]
        patched = record.patched(tone_hz=103.5)
        assert patched.raw[OFF_TONE_MODE] == TONE_CTCSS_ENC
        assert patched.raw[OFF_TX_TONE] == 13  # index of 103.5

    def test_export_never_sets_tone_squelch(self, resolved):
        """No channel in the shipped plan may be programmed tone-squelched."""
        from wasds150.export.ftx1_file import OFF_TONE_MODE, TONE_CTCSS_ENC_DEC

        _template_or_skip()
        rendered, _result = render_ftx1(resolved)
        squelched = [
            r for r in rendered.records[:MEMORY_CAPACITY]
            if not r.empty and r.raw[OFF_TONE_MODE] == TONE_CTCSS_ENC_DEC
        ]
        assert not squelched, (
            f"{len(squelched)} channels would stay muted unless the far end "
            "sends a matching tone"
        )
