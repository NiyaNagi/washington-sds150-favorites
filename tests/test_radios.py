"""Radio capability profiles and catalog tone parsing."""
import pytest

from wasds150.hpe import validation
from wasds150.radios import parse_tone
from wasds150.radios.profile import RadioProfile
from wasds150.radios.registry import FTX1, SDS150, TD_H9, get_profile, profile_ids
from wasds150.radios.tones import (
    TONE_COLOR_CODE,
    TONE_CTCSS,
    TONE_DCS,
    TONE_NAC,
    TONE_NONE,
    TONE_UNKNOWN,
)


class TestRegistry:
    def test_known_radios_are_registered(self):
        assert profile_ids() == ["ftx1", "sds150", "td-h9", "th-d75"]

    def test_lookup_is_case_insensitive(self):
        assert get_profile("TD-H9") is TD_H9

    def test_unknown_radio_names_the_alternatives(self):
        with pytest.raises(KeyError) as excinfo:
            get_profile("uv-5r")
        assert "td-h9" in str(excinfo.value)


class TestSds150Profile:
    def test_matches_the_validator_it_replaced(self):
        # The HPE writer's coverage rules must not have changed when they
        # moved onto the profile.
        assert validation._SCANNER_BANDS == SDS150.rx_bands
        assert validation._MODES == set(SDS150.modes)

    def test_is_receive_only(self):
        assert SDS150.receive_only
        assert not SDS150.can_transmit(146.52)

    @pytest.mark.parametrize("freq", [25.0, 154.28, 512.0, 855.7375, 1250.0])
    def test_accepts_in_band_frequencies(self, freq):
        assert SDS150.can_receive(freq)

    @pytest.mark.parametrize("freq", [24.0, 700.0, 830.0, 1000.0])
    def test_rejects_out_of_band_frequencies(self, freq):
        assert not SDS150.can_receive(freq)

    def test_supports_trunking(self):
        assert SDS150.supports_trunking and SDS150.supports_talkgroups


class TestTdH9Profile:
    def test_capacity_and_display_limits(self):
        assert TD_H9.max_channels == 199
        assert TD_H9.name_max_len == 8
        assert not TD_H9.supports_banks

    @pytest.mark.parametrize("freq", [121.5, 146.52, 162.55, 462.5625, 155.16])
    def test_receives_the_bands_we_plan_for(self, freq):
        assert TD_H9.can_receive(freq)

    @pytest.mark.parametrize(
        "freq,why",
        [
            (45.2, "low band CEMNET"),
            (27.185, "CB"),
            (773.10625, "700 MHz public safety"),
            (851.0125, "800 MHz interop"),
            (1250.0, "23 cm"),
        ],
    )
    def test_cannot_receive_what_the_scanner_can(self, freq, why):
        assert not TD_H9.can_receive(freq), why

    def test_is_analog_only(self):
        assert TD_H9.modes == frozenset({"AM", "FM", "NFM"})
        for digital in ("P25", "DMR", "NXDN"):
            assert not TD_H9.supports_mode(digital)

    def test_transmits_on_licensed_bands(self):
        assert TD_H9.can_transmit(146.52)
        assert TD_H9.can_transmit(446.0)
        assert TD_H9.can_transmit(462.5625)

    def test_cannot_transmit_outside_its_hardware_range(self):
        assert not TD_H9.can_transmit(121.5)
        assert not TD_H9.can_transmit(600.0)

    def test_profile_describes_hardware_not_permission(self):
        # The unlocked H9 can physically key up on NOAA weather and marine
        # VHF. Keeping the operator off them is a plan-level decision, not a
        # capability, so the profile must not pretend the radio cannot do it.
        assert TD_H9.can_transmit(162.55)
        assert TD_H9.can_transmit(156.800)


class TestFtx1Profile:
    def test_is_marked_unverified_until_checked_against_the_manual(self):
        assert not FTX1.verified

    def test_covers_hf_which_no_other_profile_does(self):
        assert FTX1.can_receive(14.2)
        assert not SDS150.can_receive(14.2)
        assert not TD_H9.can_receive(14.2)


class TestProfileValidation:
    def test_band_edges_tolerate_representation_error(self):
        profile = RadioProfile(
            id="t", vendor="v", model="m", rx_bands=((100.0, 200.0),), modes=frozenset({"FM"})
        )
        assert profile.can_receive(200.0)
        assert not profile.can_receive(200.5)

    def test_inverted_band_is_rejected(self):
        with pytest.raises(ValueError, match="high below low"):
            RadioProfile(
                id="t", vendor="v", model="m", rx_bands=((200.0, 100.0),), modes=frozenset()
            )

    def test_missing_frequency_is_never_receivable(self):
        assert not TD_H9.can_receive(None)
        assert not TD_H9.can_transmit(None)


class TestToneParsing:
    @pytest.mark.parametrize(
        "raw,kind,ctcss,dcs",
        [
            ("TONE=C127.3", TONE_CTCSS, 127.3, None),
            ("TONE=C100", TONE_CTCSS, 100.0, None),
            ("D023", TONE_DCS, None, "023"),
            ("TONE=D754", TONE_DCS, None, "754"),
            ("NAC=293", TONE_NAC, None, None),
            ("NAC=Srch", TONE_NAC, None, None),
            ("ColorCode=1", TONE_COLOR_CODE, None, None),
            ("", TONE_NONE, None, None),
            (None, TONE_NONE, None, None),
        ],
    )
    def test_parses_catalog_notation(self, raw, kind, ctcss, dcs):
        spec = parse_tone(raw)
        assert spec.kind == kind
        assert spec.ctcss_hz == ctcss
        assert spec.dcs_code == dcs

    def test_unparseable_tone_is_reported_not_guessed(self):
        spec = parse_tone("PL 127.3")
        assert spec.kind == TONE_UNKNOWN
        assert spec.ctcss_hz is None

    def test_dcs_digits_must_be_octal(self):
        assert parse_tone("D089").kind == TONE_UNKNOWN

    def test_only_ctcss_and_dcs_are_analog_squelch(self):
        assert parse_tone("TONE=C127.3").is_analog_squelch
        assert parse_tone("D023").is_analog_squelch
        assert not parse_tone("NAC=293").is_analog_squelch
        assert not parse_tone("ColorCode=1").is_analog_squelch
        assert not parse_tone("").is_analog_squelch
