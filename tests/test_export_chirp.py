"""CHIRP Generic CSV export."""
import csv
import io

import pytest

from wasds150.export.chirp_csv import CSV_HEADER, channel_to_row, render_chirp_csv
from wasds150.export.registry import get_target, targets_for_radio
from wasds150.export.report import render_plan_report
from wasds150.models.plan import TX_REPEATER, TX_SIMPLEX, ChannelSelector, PlanBlock
from wasds150.plan.resolve import resolve_plan

from test_plan import ALL, make_catalog, make_channel, simple_plan


def render(*channels, tx_policy="none", power="5.0W"):
    catalog = make_catalog(*channels)
    plan = simple_plan(PlanBlock("Block", (ALL,), tx_policy=tx_policy, power=power))
    return render_chirp_csv(resolve_plan(plan, catalog))


def rows(result):
    return list(csv.DictReader(io.StringIO(result.text)))


class TestCsvShape:
    def test_header_matches_chirp_exactly(self):
        result = render(make_channel("Test", 155.16))
        first_line = result.text.splitlines()[0]
        assert first_line == ",".join(CSV_HEADER)

    def test_header_starts_with_location_so_chirp_detects_the_file(self):
        assert CSV_HEADER[0] == "Location"

    def test_every_row_has_twenty_one_columns(self):
        result = render(
            make_channel("A", 155.16), make_channel("B", 146.52), make_channel("C", 121.5)
        )
        reader = csv.reader(io.StringIO(result.text))
        assert all(len(row) == 21 for row in reader)

    def test_file_parses_as_csv(self):
        result = render(make_channel("Quoted, Name", 155.16, notes="has, commas"))
        parsed = rows(result)
        assert len(parsed) == 1

    def test_empty_plan_still_writes_a_header(self):
        catalog = make_catalog(make_channel("Out of band", 851.0))
        result = render_chirp_csv(resolve_plan(simple_plan(PlanBlock("B", (ALL,))), catalog))
        assert result.rows == 0
        assert result.text.strip() == ",".join(CSV_HEADER)


class TestRequiredColumns:
    def test_power_is_always_written(self):
        # A blank Power column makes CHIRP silently default to 50 W.
        result = render(make_channel("Test", 155.16), power="2.0W")
        assert rows(result)[0]["Power"] == "2.0W"

    def test_frequency_uses_six_decimal_places(self):
        result = render(make_channel("Test", 155.16))
        assert rows(result)[0]["Frequency"] == "155.160000"

    def test_location_is_the_slot_number(self):
        result = render(make_channel("A", 155.16), make_channel("B", 155.28))
        assert [r["Location"] for r in rows(result)] == ["1", "2"]

    def test_name_fits_the_radio_display(self):
        result = render(make_channel("Olympic National Park Dispatch", 155.16))
        assert len(rows(result)[0]["Name"]) <= 8


class TestDuplex:
    def test_receive_only_channels_are_transmit_inhibited(self):
        result = render(make_channel("Marine 16", 156.8))
        assert rows(result)[0]["Duplex"] == "off"

    def test_simplex_transmit_leaves_duplex_blank(self):
        result = render(make_channel("Calling", 146.52), tx_policy=TX_SIMPLEX)
        assert rows(result)[0]["Duplex"] == ""

    def test_positive_offset_repeater(self):
        result = render(
            make_channel("GMRS RPT", 462.550, tx_freq_mhz=467.550), tx_policy=TX_REPEATER
        )
        row = rows(result)[0]
        assert row["Duplex"] == "+"
        assert row["Offset"] == "5.000000"

    def test_negative_offset_repeater(self):
        result = render(
            make_channel("2m RPT", 146.960, tx_freq_mhz=146.360), tx_policy=TX_REPEATER
        )
        row = rows(result)[0]
        assert row["Duplex"] == "-"
        assert row["Offset"] == "0.600000"

    def test_odd_split_is_expressed_as_a_shift(self):
        result = render(
            make_channel("Odd", 145.110, tx_freq_mhz=144.310), tx_policy=TX_REPEATER
        )
        row = rows(result)[0]
        assert row["Duplex"] == "-"
        assert row["Offset"] == "0.800000"


class TestTones:
    def test_monitoring_channels_carry_no_tone(self):
        result = render(make_channel("Dispatch", 155.16, tone="TONE=C127.3"))
        row = rows(result)[0]
        assert row["Tone"] == ""

    def test_ctcss_repeater_transmits_tone_with_open_receive_squelch(self):
        result = render(
            make_channel("RPT", 146.96, tx_freq_mhz=146.36, tone="TONE=C103.5"),
            tx_policy=TX_REPEATER,
        )
        row = rows(result)[0]
        assert row["Tone"] == "Tone"
        assert row["rToneFreq"] == "103.5"

    def test_dcs_repeater_uses_a_transmit_only_cross_mode(self):
        result = render(
            make_channel("RPT", 146.96, tx_freq_mhz=146.36, tone="D023"),
            tx_policy=TX_REPEATER,
        )
        row = rows(result)[0]
        assert row["Tone"] == "Cross"
        assert row["CrossMode"] == "DTCS->"
        assert row["DtcsCode"] == "023"

    def test_nonstandard_ctcss_is_refused_not_rounded(self):
        result = render(
            make_channel("RPT", 146.96, tx_freq_mhz=146.36, tone="TONE=C128.0"),
            tx_policy=TX_REPEATER,
        )
        assert rows(result)[0]["Tone"] == ""
        assert any("not a standard tone" in w for w in result.warnings)

    def test_defaults_are_valid_chirp_values(self):
        result = render(make_channel("Plain", 155.16))
        row = rows(result)[0]
        assert row["rToneFreq"] == "88.5"
        assert row["DtcsCode"] == "023"
        assert row["DtcsPolarity"] == "NN"


class TestModeAndSkip:
    def test_airband_is_am(self):
        result = render(make_channel("Tower", 118.1))
        assert rows(result)[0]["Mode"] == "AM"

    def test_land_mobile_is_narrow(self):
        result = render(make_channel("Dispatch", 155.16))
        assert rows(result)[0]["Mode"] == "NFM"

    def test_skip_flag_is_written(self):
        catalog = make_catalog(make_channel("Reserved", 155.16))
        plan = simple_plan(PlanBlock("B", (ALL,), skip_scan=True))
        result = render_chirp_csv(resolve_plan(plan, catalog))
        assert rows(result)[0]["Skip"] == "S"


class TestRegistry:
    def test_td_h9_has_a_target(self):
        assert [t.id for t in targets_for_radio("td-h9")] == ["chirp-csv"]

    def test_ftx1_target_is_declared_but_not_implemented(self):
        with pytest.raises(NotImplementedError, match="not implemented"):
            get_target("rtsystems-csv")

    def test_unknown_target_names_alternatives(self):
        with pytest.raises(KeyError, match="chirp-csv"):
            get_target("nope")

    def test_target_refuses_a_plan_for_another_radio(self):
        catalog = make_catalog(make_channel("Ham", 146.52))
        resolved = resolve_plan(
            simple_plan(PlanBlock("B", (ALL,)), radio_id="ftx1"), catalog
        )
        with pytest.raises(ValueError, match="targets 'ftx1'"):
            get_target("chirp-csv").check_radio(resolved)


class TestReport:
    def test_report_shows_what_was_excluded_and_why(self):
        catalog = make_catalog(
            make_channel("Keep", 155.16),
            make_channel("800 MHz", 851.0125),
        )
        resolved = resolve_plan(simple_plan(PlanBlock("Block", (ALL,))), catalog)
        report = render_plan_report(resolved)
        assert "no-rx-coverage" in report
        assert "800 MHz" in report
        assert "1 of 199 available" in report
