"""RT Systems ``.FTX1`` file reading and writing."""
import pathlib

import pytest

from wasds150.export.ftx1_file import (
    CTCSS_TONES,
    DUPLEX_MINUS,
    DUPLEX_PLUS,
    DUPLEX_SIMPLEX,
    HEADER_LEN,
    OFF_DUPLEX,
    PMS_FIRST,
    PMS_PAIRS,
    RECORD_LEN,
    Ftx1File,
    Ftx1Record,
)

SOURCE = pathlib.Path(r"Z:\Texts\HAM\Radio Programming\FTX1 WA.FTX1")

pytestmark = pytest.mark.skipif(
    not SOURCE.exists(), reason="operator's FTX-1 file is not available"
)


@pytest.fixture(scope="module")
def original() -> bytes:
    return SOURCE.read_bytes()


@pytest.fixture(scope="module")
def ftx1(original) -> Ftx1File:
    return Ftx1File.load(SOURCE)


class TestRoundTrip:
    def test_parses_and_round_trips_byte_identically(self, ftx1, original):
        # The format is undocumented, so an exact round trip is the only
        # evidence that the record model matches reality.
        assert ftx1.round_trips(original)

    def test_rejects_a_file_that_is_not_ftx1(self, tmp_path):
        path = tmp_path / "bogus.FTX1"
        path.write_bytes(b"not a yaesu file" + b"\x00" * 1000)
        with pytest.raises(ValueError, match="not an RT Systems"):
            Ftx1File.load(path)


class TestKnownRecords:
    def test_first_memory_is_the_first_weather_channel(self, ftx1):
        record = ftx1.records[0]
        assert record.name == "Weather1"
        assert record.rx_mhz == pytest.approx(162.400)
        assert record.in_use

    def test_frs_channel_one(self, ftx1):
        record = ftx1.records[7]
        assert record.name == "FRS 01"
        assert record.rx_mhz == pytest.approx(462.5625)

    def test_home_channels_hold_the_documented_defaults(self, ftx1):
        home = [r.rx_mhz for r in ftx1.records[1189:1194]]
        assert home == pytest.approx([29.600, 51.525, 118.000, 146.520, 446.000])


class TestInUseFlag:
    def test_an_unflagged_record_reads_as_empty(self, ftx1):
        # This is the flag that decides whether the programmer shows a row.
        # A record can hold a frequency and still be invisible without it.
        blank = ftx1.records[900]
        assert not blank.in_use
        assert blank.empty

    def test_writing_a_frequency_marks_the_record_in_use(self, ftx1):
        patched = ftx1.records[900].patched(rx_hz=14_000_000)
        assert patched.in_use
        assert not patched.empty

    def test_in_use_can_be_cleared_explicitly(self, ftx1):
        patched = ftx1.records[0].patched(in_use=False)
        assert not patched.in_use


class TestDuplex:
    def test_duplex_byte_follows_the_frequencies(self, ftx1):
        template = ftx1.records[0]
        simplex = template.patched(rx_hz=146_520_000, tx_hz=146_520_000)
        minus = template.patched(rx_hz=146_960_000, tx_hz=146_360_000)
        plus = template.patched(rx_hz=442_050_000, tx_hz=447_050_000)
        assert simplex.raw[OFF_DUPLEX] == DUPLEX_SIMPLEX
        assert minus.raw[OFF_DUPLEX] == DUPLEX_MINUS
        assert plus.raw[OFF_DUPLEX] == DUPLEX_PLUS

    def test_existing_records_agree_with_their_own_frequencies(self, ftx1):
        for record in ftx1.memories():
            if record.empty:
                continue
            if record.tx_hz == record.rx_hz:
                expected = DUPLEX_SIMPLEX
            elif record.tx_hz > record.rx_hz:
                expected = DUPLEX_PLUS
            else:
                expected = DUPLEX_MINUS
            assert record.raw[OFF_DUPLEX] == expected, record.name


class TestTones:
    def test_decodes_a_known_tone(self, ftx1):
        toned = [r for r in ftx1.memories() if not r.empty and r.tx_tone_hz]
        assert len(toned) > 300
        assert all(t.tx_tone_hz in CTCSS_TONES for t in toned)

    def test_writes_a_standard_tone(self, ftx1):
        patched = ftx1.records[0].patched(rx_hz=146_960_000, tone_hz=103.5)
        assert patched.tx_tone_hz == 103.5

    def test_refuses_a_nonstandard_tone(self, ftx1):
        with pytest.raises(ValueError, match="not a standard CTCSS tone"):
            ftx1.records[0].patched(tone_hz=128.0)


class TestScanLimits:
    def test_scan_pairs_start_after_the_last_memory(self):
        assert PMS_FIRST == 999
        assert PMS_PAIRS == 50

    def test_setting_a_pair_writes_both_limits(self, ftx1, original):
        working = Ftx1File.load(SOURCE)
        working.set_scan_limit(0, 14.000, 14.350, label="20m")
        low, high = working.scan_limits()[0]
        assert low.rx_mhz == pytest.approx(14.000)
        assert high.rx_mhz == pytest.approx(14.350)
        assert low.in_use and high.in_use
        # Writing must not change the file's size or shift any other record.
        assert len(working.to_bytes()) == len(original)

    def test_inverted_range_is_refused(self, ftx1):
        working = Ftx1File.load(SOURCE)
        with pytest.raises(ValueError, match="must be above"):
            working.set_scan_limit(0, 14.350, 14.000)

    def test_pair_index_is_bounded(self, ftx1):
        working = Ftx1File.load(SOURCE)
        with pytest.raises(ValueError, match="outside"):
            working.set_scan_limit(PMS_PAIRS, 14.0, 14.35)


class TestWriting:
    def test_patching_never_changes_record_length(self, ftx1):
        patched = ftx1.records[0].patched(
            rx_hz=146_520_000, name="A" * 40, comment="B" * 80
        )
        assert len(patched.raw) == RECORD_LEN

    def test_a_written_file_reloads_identically(self, ftx1, tmp_path):
        working = Ftx1File.load(SOURCE)
        working.set_scan_limit(3, 7.000, 7.300, label="40m")
        out = tmp_path / "out.FTX1"
        working.save(out)
        assert Ftx1File.load(out).to_bytes() == working.to_bytes()

    def test_header_length_places_record_zero_correctly(self, ftx1, original):
        assert HEADER_LEN == 0x5E
        assert ftx1.records[0].raw == original[HEADER_LEN : HEADER_LEN + RECORD_LEN]
