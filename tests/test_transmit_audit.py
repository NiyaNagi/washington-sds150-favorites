"""Transmit follows the service, and every radio is checked before it is written.

These tests are the standing form of the radio audit: a fleet plan may never
block transmit on a channel the operator is licensed for, never transmit
where they are not, and the WWARA checks must catch a wrong call, input or
access tone. See CLAUDE.md and wasds150.plan.audit.
"""
import datetime
import io
import zipfile

from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import TX_NONE, TX_REPEATER, ChannelPlan, ChannelSelector, PlanBlock
from wasds150.plan.coordination import STATUS_CURRENT, STATUS_EXPIRED, STATUS_PENDING, index_from_zip
from wasds150.plan.resolve import resolve_plan


def _catalog(*channels):
    department = Department(id="d", label="Mixed", channels=list(channels))
    favorite = FavoritesList(
        id="f", slug="mix", favorite_key="MIX", favorite_name="Mixed", region="", counties="", scenario="",
        source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
        monitorability="", upgrade_required="", source_url="", notes="",
        systems=[System(id="s", label="S", departments=[department])],
    )
    return Catalog(favorites=[favorite])


def _plan(block_policy=TX_NONE, *, by_service=True, radio_id="td-h9"):
    block = PlanBlock("Other Nearby", (ChannelSelector(favorite_keys=("MIX",)),), tx_policy=block_policy)
    return ChannelPlan(
        id="t", radio_id=radio_id, label="t", blocks=(block,), license_class="general",
        gmrs_licensed=True, murs_transmit=True, transmit_by_service=by_service,
    )


def _by_label(resolved):
    return {c.label: c for c in resolved.channels}


# ------------------------------------------------------------ transmit rule --
def test_licensed_services_transmit_in_any_block_and_nothing_else_does():
    resolved = resolve_plan(_plan(), _catalog(
        Channel(id="r", label="KC7BAE E Tiger", freq_mhz=443.05, tx_freq_mhz=448.05, tone="TONE=C103.5", mode="FM"),
        Channel(id="s", label="Double Nickel Net", freq_mhz=146.55, mode="FM"),
        Channel(id="g", label="FRS 7", freq_mhz=462.7125, mode="NFM"),
        Channel(id="m", label="MURS 2", freq_mhz=151.88, mode="NFM"),
        Channel(id="b", label="MedNet 10", freq_mhz=462.975, mode="NFM"),
        Channel(id="c", label="Marine 16", freq_mhz=156.8, mode="FM"),
    ))
    channels = _by_label(resolved)
    tiger = channels["KC7BAE E Tiger"]
    assert (tiger.transmit, tiger.tx_freq_mhz, tiger.tx_tone.ctcss_hz) == (True, 448.05, 103.5)
    assert channels["Double Nickel Net"].transmit and channels["Double Nickel Net"].tx_freq_mhz is None
    assert channels["FRS 7"].transmit and channels["MURS 2"].transmit
    # MedNet sits inside the radio's transmit coverage but is Part 90: no licence.
    assert not channels["MedNet 10"].transmit and not channels["Marine 16"].transmit


def test_a_repeater_without_a_usable_input_transmits_simplex_in_a_fleet_plan():
    resolved = resolve_plan(_plan(TX_REPEATER), _catalog(
        Channel(id="n", label="Simplex Net", freq_mhz=146.58, mode="FM"),
        Channel(id="e", label="Echo", freq_mhz=147.6, tx_freq_mhz=147.6, mode="FM"),
    ))
    assert all(c.transmit and c.tx_freq_mhz is None for c in resolved.channels)
    assert any("transmits simplex" in w for w in resolved.warnings)


def test_a_hand_written_plan_keeps_its_block_policy():
    catalog = _catalog(Channel(id="r", label="Repeater", freq_mhz=443.05, tx_freq_mhz=448.05, mode="FM"))
    assert not resolve_plan(_plan(by_service=False), catalog).channels[0].transmit


def test_licence_class_privileges_still_apply_by_service():
    resolved = resolve_plan(_plan(radio_id="ftx1"), _catalog(
        Channel(id="x", label="75m Extra", freq_mhz=3.75, mode="LSB"),
        Channel(id="g", label="75m General", freq_mhz=3.9, mode="LSB"),
    ))
    channels = _by_label(resolved)
    assert not channels["75m Extra"].transmit and channels["75m General"].transmit


# ------------------------------------------------------------- coordination --
_HEADER = "FC_RECORD_ID,OUTPUT_FREQ,INPUT_FREQ,STATE,CITY,CALL,CTCSS_IN,CTCSS_OUT,DCS_CDCSS,DMR,DSTAR_DV,EXPIRATION_DATE"


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, rows in files.items():
            archive.writestr(name, "DATA_SPEC_VERSION=2015.2.2\n" + _HEADER + "\n" + "\n".join(rows) + "\n")
    return buffer.getvalue()


def _coordination():
    return index_from_zip(_zip({
        "WWARA-rptrlist-20260913.csv": [
            "1,443.0500,448.0500,WA,Bremerton,N7MTC,100,100,,N,N,2025-11-24",
            "2,444.1750,449.1750,WA,Tacoma,K7HW,103.5,103.5,,N,N,2029-12-06",
            "4,147.0600,147.6600,WA,Chehalis,K7PG,110.9,110.9,,N,N,2029-01-01",
            "5,147.0600,147.6600,WA,Clallam Bay,W7FEL,100,100,,N,N,2029-01-01",
            "6,147.3200,147.9200,WA,Kent,N7RHE,103.5,103.5,,N,N,2027-03-02",
            "7,444.0750,449.0750,WA,Bremerton,KC7Z,103.5,103.5,,N,N,2030-04-03",
        ],
        "WWARA-pending-rptrlist-20260913.csv": ["3,443.0500,448.0500,WA,Tiger Mtn East,KC7BAE,103.5,103.5,,N,N,"],
        "WWARA-Expired-20260913.csv": ["1,443.0500,448.0500,WA,Bremerton,N7MTC,100,100,,N,N,2025-11-24"],
    }), today=datetime.date(2026, 9, 13))


def test_the_coordination_index_reads_every_list_and_trusts_the_expiry_date():
    index = _coordination()
    assert index.source_date == "2026-09-13" and len(index) == 7
    assert {r.call: r.status for r in index.on_output(443.05)} == {"N7MTC": STATUS_EXPIRED, "KC7BAE": STATUS_PENDING}
    [k7hw] = index.on_output(444.175)
    assert (k7hw.status, k7hw.input_mhz, k7hw.ctcss_in) == (STATUS_CURRENT, 449.175, 103.5)


# ---------------------------------------------------------------- the audit --
def _planned(slot, label, rx, *, tx=None, tone="", transmit=True, mode="FM"):
    from wasds150.plan.resolve import PlannedChannel
    from wasds150.radios.tones import parse_tone

    return PlannedChannel(slot=slot, name=label, label=label, rx_freq_mhz=rx, mode=mode, block="Ham",
                          source="TEST/Dept", transmit=transmit, tx_freq_mhz=tx, tx_tone=parse_tone(tone))


def _resolved(*channels, radio_id="th-d75"):
    from wasds150.plan.resolve import ResolvedPlan
    from wasds150.radios.registry import get_profile

    plan = ChannelPlan(id="t", radio_id=radio_id, label="t", license_class="general", gmrs_licensed=True,
                       murs_transmit=True, transmit_by_service=True)
    return ResolvedPlan(plan=plan, profile=get_profile(radio_id), channels=list(channels))


def _codes(findings):
    return sorted((f.code, f.name) for f in findings)


def test_the_audit_flags_blocked_and_unlicensed_transmit():
    from wasds150.plan.audit import audit_plan

    findings = audit_plan("th-d75", _resolved(
        _planned(1, "N7MTC Bremerton", 443.05, transmit=False),
        _planned(2, "Marine 16", 156.8),
        _planned(3, "Airport", 121.5, transmit=False, mode="AM"),
    ))
    assert _codes(findings) == [("transmit-blocked", "N7MTC Bremerton"), ("transmit-unlicensed", "Marine 16")]


def test_the_audit_checks_call_input_and_tone_against_wwara():
    from wasds150.plan.audit import ERROR, audit_plan

    findings = audit_plan("th-d75", _resolved(
        _planned(1, "KC7BAE E Tiger", 443.05, tx=448.05, tone="TONE=C103.5"),   # pending coordination: right
        _planned(2, "K7HW - Tacoma", 444.175, tx=449.175, tone="TONE=C123.0"),  # wrong access tone
        _planned(3, "K7HW Tacoma alt", 444.175, tx=444.775, tone="TONE=C103.5"),  # wrong input
        _planned(4, "W7FEL (Clallam Bay)", 147.06, tx=147.66, tone="TONE=C110.9"),  # K7PG's tone on the pair
        _planned(5, "N7MTC Bremerton", 443.05, tx=448.05, tone="TONE=C100"),    # lapsed
        _planned(6, "K7CST Kent", 147.32, tx=147.92, tone="TONE=C103.5"),        # N7RHE's machine, at Kent
        _planned(7, "Carlsborg W7FEL", 147.06, tx=147.66, tone="TONE=C77"),      # a second machine on the pair
    ), _coordination())
    assert _codes(findings) == sorted([
        ("coordination-tone", "K7HW - Tacoma"),
        ("coordination-input", "K7HW Tacoma alt"),
        ("repeater-offset", "K7HW Tacoma alt"),
        ("conflicting-copies", "K7HW Tacoma alt"),
        ("coordination-call", "W7FEL (Clallam Bay)"),
        ("coordination-expired", "N7MTC Bremerton"),
        ("coordination-call", "K7CST Kent"),
        ("coordination-tone", "Carlsborg W7FEL"),
        ("conflicting-copies", "Carlsborg W7FEL"),
    ])
    severities = {(f.code, f.name): f.severity for f in findings}
    # Named for the coordinated machine's own city: the record wins.
    assert severities[("coordination-call", "K7CST Kent")] == ERROR
    # Not placed at K7PG's site: a human decides.
    assert severities[("coordination-call", "W7FEL (Clallam Bay)")] != ERROR


def test_a_shared_pair_note_and_a_filled_tone_are_not_findings():
    from wasds150.plan.audit import audit_plan
    from wasds150.plan.coordination import fill_access_tones

    carlsborg = _planned(1, "Carlsborg W7FEL", 147.06, tx=147.66, tone="TONE=C77")
    carlsborg.comment = "Carlsborg repeater on a shared pair with Striped Peak, on a different tone"
    toneless = _planned(2, "KC7Z Kitsap row", 444.075, tx=449.075)
    resolved = _resolved(carlsborg, toneless)
    assert fill_access_tones(resolved, _coordination()) == 1
    assert toneless.tx_tone.ctcss_hz == 103.5
    assert audit_plan("th-d75", resolved, _coordination()) == []


def test_a_memory_named_for_one_machine_on_a_shared_pair_takes_its_tone():
    from wasds150.plan.audit import audit_plan
    from wasds150.plan.coordination import fill_access_tones

    chehalis = _planned(1, "K7PG Chehalis", 147.06, tx=147.66)
    unnamed = _planned(2, "Lewis County row", 147.06, tx=147.66)
    lapsed = _planned(3, "N7MTC Bremerton", 443.05, tx=448.05)
    resolved = _resolved(chehalis, unnamed, lapsed)
    # K7PG and W7FEL share the pair on different tones: only the named memory is
    # filled. N7MTC's coordination lapsed, but the memory is named for it.
    assert fill_access_tones(resolved, _coordination()) == 2
    assert chehalis.tx_tone.ctcss_hz == 110.9 and unnamed.tx_tone.ctcss_hz is None and lapsed.tx_tone.ctcss_hz == 100
    findings = audit_plan("th-d75", resolved, _coordination())
    assert not [f for f in findings if f.name == "K7PG Chehalis" or f.code == "coordination-tone"]


def test_the_exported_th_d75_file_is_checked_for_the_ptt_inhibit_split(tmp_path):
    from pathlib import Path

    from wasds150.export.thd75_target import write_thd75
    from wasds150.plan.audit import audit_export

    template = Path(__file__).resolve().parents[1] / "radio-data" / "th-d75" / "reference" / "current" / "thd75-current.d75"
    keyed = _resolved(_planned(1, "KC7BAE E Tiger", 443.05, tx=448.05, tone="TONE=C103.5"))
    blocked = _resolved(_planned(1, "KC7BAE E Tiger", 443.05, transmit=False))
    good, bad = tmp_path / "good.d75", tmp_path / "bad.d75"
    write_thd75(keyed, good, template=template)
    write_thd75(blocked, bad, template=template)
    assert audit_export("th-d75", keyed, good) == []
    assert [f.code for f in audit_export("th-d75", keyed, bad)] == ["export-transmit-blocked"]


def test_two_machines_sharing_a_pair_keep_their_own_names():
    from wasds150.catalog.labels import StationLabels

    def repeater(id, label, tone):
        return Channel(id=id, label=label, freq_mhz=147.06, tx_freq_mhz=147.66, tone=tone, mode="FM",
                       lat=46.6, lon=-123.0)

    k7pg, w7fel, acs = (repeater("a", "K7PG Baw Faw", "TONE=C110.9"), repeater("b", "W7FEL Clallam Bay", "TONE=C100"),
                        repeater("c", "V36 ACS", "TONE=C110.9"))
    labels = StationLabels([("PSHAM01", None, k7pg), ("PSHAM01", None, w7fel), ("SEAACS", None, acs)], home=(47.6, -122.0))
    assert labels.label(None, acs) == "K7PG Baw Faw"
    assert labels.label(None, w7fel) == "W7FEL Clallam Bay"


def test_a_toneless_copy_of_a_keyed_repeater_is_not_programmed_twice():
    resolved = resolve_plan(_plan(), _catalog(
        Channel(id="r", label="K7LED Tiger", freq_mhz=146.82, tx_freq_mhz=146.22, tone="TONE=C103.5", mode="FM"),
        Channel(id="c", label="K7LED county row", freq_mhz=146.82, tx_freq_mhz=146.22, mode="FM"),
    ))
    assert [c.label for c in resolved.channels] == ["K7LED Tiger"]


def test_no_fleet_plan_blocks_licensed_transmit_or_transmits_unlicensed(tmp_path_factory):
    from conftest import REPO_CSV_PATH

    from wasds150.appctx import build_context
    from wasds150.config import AppConfig
    from wasds150.plan.audit import ERROR, audit_plan
    from wasds150.plan.service import resolve_named_plan
    from wasds150.plans.template import FLEET_PLAN_RADIOS, fleet_plan_id

    config = AppConfig(home=tmp_path_factory.mktemp("home"))
    config.ensure_dirs()
    ctx = build_context(config, csv_override=REPO_CSV_PATH)
    for radio_id in FLEET_PLAN_RADIOS:
        _plan_, resolved = resolve_named_plan(ctx, fleet_plan_id(radio_id))
        errors = [f.line() for f in audit_plan(radio_id, resolved) if f.severity == ERROR]
        assert errors == [], radio_id


def test_a_dcs_machine_is_not_named_for_the_ctcss_machine_on_its_pair():
    from wasds150.catalog.labels import StationLabels

    ww7ch = Channel(id="a", label="WW7CH - Ashford", freq_mhz=146.78, tx_freq_mhz=146.18, tone="TONE=C103.5",
                    mode="FM", lat=46.76, lon=-121.95)
    lynnwood = Channel(id="b", label="V71 Lynwood", freq_mhz=146.78, tx_freq_mhz=146.18, tx_tone="D172", mode="FM",
                       lat=46.76, lon=-121.95)
    labels = StationLabels([("PSHAM01", None, ww7ch), ("SEAACS", None, lynnwood)], home=(47.6, -122.0))
    assert labels.label(None, lynnwood) == "V71 Lynwood"


def test_a_source_tone_correction_follows_every_rebuild_of_the_list():
    from wasds150.recipes.dmr_corrections import correct_network_lists

    acs = FavoritesList(
        id="acs", slug="seaacs", favorite_key="SEAACS", favorite_name="ACS", region="", counties="", scenario="",
        source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
        monitorability="", upgrade_required="", source_url="", notes="",
        systems=[System(id="s", label="S", departments=[Department(id="d", label="ACS UHF", channels=[
            Channel(id="u71", label="U71 Mountlake", freq_mhz=443.725, tx_freq_mhz=448.725,
                    tone="TONE=C103.5", tx_tone="TONE=C103.5", mode="NFM"),
        ])])],
    )
    [fixed] = correct_network_lists([acs])
    channel = fixed.systems[0].departments[0].channels[0]
    assert (channel.tone, channel.tx_tone) == ("TONE=C156.7", "TONE=C156.7")
    assert acs.systems[0].departments[0].channels[0].tone == "TONE=C103.5"  # the catalog copy is untouched
