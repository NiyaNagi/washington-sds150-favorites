"""A radio can demodulate a mode on only part of its receive coverage."""
from wasds150.models.catalog import Channel
from wasds150.plan.resolve import resolve_mode
from wasds150.radios.registry import ID52A, TH_D75


def _channel(freq, mode):
    return Channel(id=f"{freq}", label=f"{freq}", freq_mhz=freq, mode=mode)


def test_the_id52a_has_no_am_above_375_mhz():
    # CS-52 dropped these on import; the VHF air band and 225-375 MHz AM imported.
    assert resolve_mode(_channel(393.3, "AM"), ID52A) is None
    assert resolve_mode(_channel(377.15, "AM"), ID52A) is None
    assert resolve_mode(_channel(118.3, "AM"), ID52A) == "AM"
    assert resolve_mode(_channel(282.8, "AM"), ID52A) == "AM"
    # FM up there is unaffected, and a mode with no limit works across coverage.
    assert resolve_mode(_channel(446.0, "FM"), ID52A) == "FM"
    assert ID52A.supports_mode("AM") and not ID52A.supports_mode("AM", 395.0)


def test_a_radio_without_mode_limits_is_unchanged():
    assert TH_D75.mode_bands == ()
    assert TH_D75.supports_mode("FM", 446.0) == TH_D75.supports_mode("FM")
