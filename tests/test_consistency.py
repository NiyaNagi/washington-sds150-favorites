"""Fleet-wide checks: each radio holds the right stations for its capability,
and the radios agree (wasds150.plan.consistency). Invented calls throughout."""
from wasds150.models.plan import ChannelPlan
from wasds150.plan.consistency import DStarMachine, _SourceIndex, audit_across, audit_radio
from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.models.catalog import Catalog
from wasds150.radios.registry import get_profile
from wasds150.radios.tones import parse_tone

HOME = (47.6351, -121.9954)
SOURCES = _SourceIndex(Catalog(favorites=[]))
DV_ONLY = DStarMachine("W7DVX", "B", 444.6375, 449.6375, 47.49, -121.96, False, False, False, True)
MIXED = DStarMachine("W7MIX", "B", 443.9, 448.9, 47.94, -122.02, False, True, False, True)


def _ch(slot, name, rx, *, tx=None, mode="FM", tone="", rpt1="", lat=None, lon=None, block="Ham"):
    return PlannedChannel(slot=slot, name=name, label=name, rx_freq_mhz=rx, mode=mode, block=block, source="TEST/Dept",
                          transmit=tx is not None, tx_freq_mhz=tx, tx_tone=parse_tone(tone), dv_rpt1=rpt1,
                          lat=lat, lon=lon)


def _resolved(radio_id, *channels):
    plan = ChannelPlan(id="t", radio_id=radio_id, label="t", license_class="general", transmit_by_service=True)
    return ResolvedPlan(plan=plan, profile=get_profile(radio_id), channels=list(channels))


def _codes(findings):
    return sorted((f.code, f.name) for f in findings)


def _stations(findings):
    """Findings about the stations present, not the pinned ones a small test plan leaves out."""
    return _codes(f for f in findings if f.code != "pinned-missing")


def test_a_d_star_only_machine_is_d_star_on_d_star_radios_and_absent_elsewhere():
    fm_copy = _ch(1, "W7DVX Tiger", 444.6375, tx=449.6375)
    th = audit_radio("th-d75", _resolved("th-d75", fm_copy), [DV_ONLY], [], SOURCES, home=HOME)
    assert ("dstar-as-analog", "W7DVX Tiger") in _codes(th)
    # The radio also has no D-STAR memory for a machine this close to home.
    assert ("dstar-missing", "W7DVX B") in _codes(th)
    anytone = audit_radio("at-d890uv", _resolved("at-d890uv", fm_copy), [DV_ONLY], [], SOURCES, home=HOME)
    assert _stations(anytone) == [("dstar-unsupported", "W7DVX Tiger")]


def test_a_mixed_machine_keeps_its_fm_memory_everywhere():
    fm = _ch(1, "W7MIX Snohomish", 443.9, tx=448.9, tone="TONE=C151.4")
    assert _stations(audit_radio("at-d890uv", _resolved("at-d890uv", fm), [MIXED], [], SOURCES, home=HOME)) == []


def test_a_d_star_memory_is_named_for_its_routing_call():
    wrong = _ch(1, "CLUBGARAGE", 444.6375, tx=449.6375, mode="DV", rpt1="W7DVX  B")
    right = _ch(2, "W7DVXBTIGER", 444.6375, tx=449.6375, mode="DV", rpt1="W7DVX  B")
    findings = audit_radio("th-d75", _resolved("th-d75", wrong, right), [DV_ONLY], [], SOURCES, home=HOME)
    assert _stations(findings) == [("dstar-name", "CLUBGARAGE")]


def test_another_call_on_the_pair_is_another_machine():
    # An FM machine under its own call sharing a D-STAR machine's pair elsewhere.
    other = _ch(1, "W7FMM Ashford", 444.6375, tx=449.6375, lat=46.83, lon=-122.02)
    assert not [f for f in audit_radio("at-d890uv", _resolved("at-d890uv", other), [DV_ONLY], [], SOURCES, home=HOME)
                if f.code.startswith("dstar")]


def test_the_pinned_station_must_be_on_a_radio_without_groups():
    findings = audit_radio("td-h9", _resolved("td-h9", _ch(1, "W7ABC", 146.52)), [], [], SOURCES, home=HOME)
    assert ("pinned-missing", "KC7BAE") in _codes(findings)


def test_one_repeater_keyed_with_different_tones_is_a_mismatch():
    a = _resolved("th-d75", _ch(1, "W7TON Hill", 146.9, tx=146.3, tone="TONE=C103.5"))
    b = _resolved("id-52a", _ch(1, "W7TON Hill", 146.9, tx=146.3, tone="TONE=C103.5"))
    c = _resolved("td-h9", _ch(1, "W7TON Hill", 146.9, tx=146.3, tone=""))
    findings = audit_across({"th-d75": a, "id-52a": b, "td-h9": c}, None)
    assert [(f.code, f.radio_id) for f in findings] == [("station-mismatch", "td-h9")]
    assert findings[0].correction == "set access tone 103.5"


def test_a_mode_the_radio_cannot_use_there_is_a_capability_violation():
    # The Anytone stores AM only in its air-band list.
    ems = _ch(1, "EMS", 462.95, mode="AM", block="Business")
    findings = audit_radio("at-d890uv", _resolved("at-d890uv", ems), [], [], SOURCES, home=HOME)
    assert ("capability-violation", "EMS") in _codes(findings)
