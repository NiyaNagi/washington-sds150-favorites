"""The fleet plan template: blocks by capability, licensed transmit, budgets."""
from __future__ import annotations

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.models.catalog import CSV_FIELDS, Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import (
    SORT_TIER_DISTANCE,
    TX_AUTO,
    TX_NONE,
    TX_SIMPLEX,
    ChannelPlan,
    ChannelSelector,
    PlanBlock,
)
from wasds150.plan.resolve import resolve_plan
from wasds150.plan.service import resolve_named_plan
from wasds150.plans import get_plan, list_plans
from wasds150.plans.template import (
    FLEET_PLAN_RADIOS,
    GMRS_INTERSTITIAL,
    GMRS_MAIN,
    HOME,
    MURS,
    SERVICE_BLOCKS_BY_ID,
    RadioKnobs,
    build_fleet_plan,
    default_knobs,
    slot_budget,
)
from wasds150.radios.bandplan import may_transmit
from wasds150.radios.registry import get_profile

#: Slots each legacy plan resolves to against the repository CSV. The fleet
#: work must not move any of them.
LEGACY_SLOTS = {
    "atd890-scan": 957,
    "ftx1-local": 188,
    "ftx1-scan": 183,
    "ftx1-wa": 855,
    "h9-ozette": 141,
    "thd75-ames-lake": 386,
    "thd75-scan": 391,
}

_PERSONAL_FREQS = set(GMRS_MAIN) | set(GMRS_INTERSTITIAL) | set(MURS)


@pytest.fixture(scope="module")
def real_ctx(tmp_path_factory):
    from conftest import REPO_CSV_PATH

    config = AppConfig(home=tmp_path_factory.mktemp("home"))
    config.ensure_dirs()
    return build_context(config, csv_override=REPO_CSV_PATH)


def _favorite(key: str, departments) -> FavoritesList:
    row = {name: "" for name in CSV_FIELDS}
    row["favorite_key"] = key
    row["favorite_name"] = key
    favorite = FavoritesList.from_csv_row(row)
    favorite.systems = [System(id=f"{key}-s", label=key, departments=list(departments))]
    return favorite


# ----------------------------------------------------------- registration --
def test_one_fleet_plan_per_memory_radio():
    for radio_id in FLEET_PLAN_RADIOS:
        plan = get_plan(f"{radio_id}-fleet")
        assert plan.radio_id == radio_id
        assert plan.license_class == "general"


def test_legacy_plans_stay_registered():
    assert set(LEGACY_SLOTS) <= set(list_plans())


def test_the_scanner_has_no_memory_plan():
    with pytest.raises(ValueError):
        build_fleet_plan("sds150")


def test_block_ceilings_never_exceed_what_the_radio_holds():
    for radio_id in FLEET_PLAN_RADIOS:
        profile = get_profile(radio_id)
        capacity = profile.max_channels - default_knobs(radio_id).reserve_slots
        assert slot_budget(radio_id) <= capacity, radio_id


def test_blocks_follow_capabilities():
    labels = {radio_id: {b.label for b in build_fleet_plan(radio_id).blocks} for radio_id in FLEET_PLAN_RADIOS}
    assert "DMR Core" in labels["at-d890uv"] and "DMR Core" not in labels["td-h9"]
    assert "D-STAR Repeaters" in labels["th-d75"] and "D-STAR Repeaters" not in labels["ftx1"]
    assert "HF Voice Nets" in labels["ftx1"] and "HF Voice Nets" not in labels["at-d890uv"]
    assert "Ham 1.25m Repeaters" in labels["th-d75"] and "Ham 1.25m Repeaters" not in labels["ftx1"]
    assert "FM Broadcast" in labels["at-d890uv"] and "FM Broadcast" not in labels["ftx1"]


def test_banks_and_scan_groups_fit_the_anytone_display():
    plan = build_fleet_plan("at-d890uv")
    assert all(block.bank and len(block.bank) <= 16 for block in plan.blocks)
    names = [group.name for group in plan.scan_groups]
    assert names[:2] == ["Ham All", "Ham Analog"] and names[-1] == "Everything"
    skipped = {block.label for block in plan.blocks if block.skip_scan}
    for group in plan.scan_groups:
        assert len(group.name) <= 13
        assert not set(group.blocks) & skipped


# --------------------------------------------------------------- transmit --
def test_transmit_only_in_licensed_blocks():
    licensed = {spec.label for spec in SERVICE_BLOCKS_BY_ID.values() if spec.tx != "none"}
    for radio_id in FLEET_PLAN_RADIOS:
        for block in build_fleet_plan(radio_id).blocks:
            if block.tx_policy != TX_NONE:
                assert block.label in licensed, (radio_id, block.label)


def test_gmrs_and_murs_transmit_wherever_the_hardware_does():
    policies = {b.label: b.tx_policy for b in build_fleet_plan("td-h9").blocks}
    assert policies["GMRS 1-7"] == TX_AUTO and policies["GMRS 15-22"] == TX_AUTO
    assert policies["MURS"] == TX_SIMPLEX
    assert policies["FRS 8-14"] == TX_NONE
    for radio_id in ("ftx1", "th-d75", "at-d890uv"):
        for block in build_fleet_plan(radio_id).blocks:
            if block.label.startswith(("GMRS", "FRS", "MURS")):
                assert block.tx_policy == TX_NONE, (radio_id, block.label)


def test_gmrs_power_respects_the_interstitial_cap():
    powers = {b.label: b.power for b in build_fleet_plan("td-h9").blocks}
    assert powers["GMRS 1-7"] == "5.0W"
    assert powers["GMRS 15-22"] == "10W"
    assert powers["MURS"] == "1.0W"


def test_no_amateur_transmit_without_a_licence():
    knobs = RadioKnobs(license_class="", gmrs_licensed=False, murs_tx=False)
    for block in build_fleet_plan("at-d890uv", knobs).blocks:
        assert block.tx_policy == TX_NONE, block.label


def test_resolved_fleet_plans_fit_and_transmit_legally(real_ctx):
    for radio_id in FLEET_PLAN_RADIOS:
        _plan, resolved = resolve_named_plan(real_ctx, f"{radio_id}-fleet")
        assert "capacity" not in resolved.drop_reasons(), radio_id
        assert resolved.slots_used > 0
        for channel in resolved.channels:
            if not channel.transmit:
                continue
            freq = channel.tx_freq_mhz if channel.tx_freq_mhz is not None else channel.rx_freq_mhz
            assert resolved.profile.can_transmit(freq), (radio_id, channel.label)
            personal = any(abs(channel.rx_freq_mhz - f) < 0.001 for f in _PERSONAL_FREQS)
            # The band plan does not model 1.25 m (no radio reached it when it
            # was written); 222-225 MHz is entirely inside General privileges.
            amateur = may_transmit(freq, "general") or 222.0 <= freq <= 225.0
            assert personal or amateur, (radio_id, channel.label, freq)


def test_legacy_plans_are_unchanged(real_ctx):
    for plan_id, slots in LEGACY_SLOTS.items():
        assert resolve_named_plan(real_ctx, plan_id)[1].slots_used == slots, plan_id


# ------------------------------------------------------ resolver additions --
def _plan(profile_id: str, block: PlanBlock, license_class: str = "") -> ChannelPlan:
    return ChannelPlan(id="t", radio_id=profile_id, label="t", blocks=(block,), license_class=license_class)


def test_licence_class_limits_amateur_transmit_with_one_warning():
    department = Department(
        id="d", label="HF",
        channels=[
            Channel(id="a", label="20m Extra", freq_mhz=14.160, mode="USB"),
            Channel(id="b", label="20m General", freq_mhz=14.300, mode="USB"),
            Channel(id="c", label="15m Extra", freq_mhz=21.210, mode="USB"),
        ],
    )
    catalog = Catalog(favorites=[_favorite("HFT", [department])])
    block = PlanBlock(label="HF", selectors=(ChannelSelector(favorite_keys=("HFT",)),), tx_policy=TX_SIMPLEX)
    resolved = resolve_plan(_plan("ftx1", block, license_class="general"), catalog, get_profile("ftx1"))
    transmit = {c.label: c.transmit for c in resolved.channels}
    assert transmit == {"20m Extra": False, "20m General": True, "15m Extra": False}
    licence_warnings = [w for w in resolved.warnings if "privileges" in w]
    assert licence_warnings == ["HF: 2 channel(s) outside general-class privileges, programmed receive-only"]


def test_tx_auto_uses_a_published_input_and_otherwise_stays_simplex():
    department = Department(
        id="d", label="GMRS",
        channels=[
            Channel(id="r", label="GMRS Rpt 15", freq_mhz=462.550, tx_freq_mhz=467.550, mode="FM"),
            Channel(id="s", label="GMRS 1", freq_mhz=462.5625, mode="FM"),
        ],
    )
    catalog = Catalog(favorites=[_favorite("GM", [department])])
    block = PlanBlock(label="GMRS", selectors=(ChannelSelector(favorite_keys=("GM",)),), tx_policy=TX_AUTO)
    resolved = resolve_plan(_plan("td-h9", block), catalog, get_profile("td-h9"))
    by_label = {c.label: c for c in resolved.channels}
    assert by_label["GMRS Rpt 15"].transmit and by_label["GMRS Rpt 15"].tx_freq_mhz == 467.55
    assert by_label["GMRS 1"].transmit and by_label["GMRS 1"].tx_freq_mhz is None
    assert not resolved.warnings


def test_tier_distance_sort_puts_near_calling_groups_first():
    near = (47.64, -122.00)
    far = (47.20, -122.40)
    def dmr(cid, tg_name, where, tg):
        return Channel(
            id=cid, label=cid, freq_mhz=440.0 + len(cid) / 1000, mode="DMR", lat=where[0], lon=where[1],
            dmr_color_code=1, dmr_timeslot=1, dmr_talkgroup=tg, dmr_talkgroup_name=tg_name, network="PNWDigital",
        )
    department = Department(
        id="d", label="Puget Sound",
        channels=[
            dmr("far-core", "PNW 1", far, 3187),
            dmr("near-wide", "Idaho 1", near, 3116),
            dmr("near-core", "Washington 1", near, 3153),
            dmr("near-test", "Parrot 1", near, 9998),
        ],
    )
    catalog = Catalog(favorites=[_favorite("DMRNET", [department])])
    selector = ChannelSelector(favorite_keys=("DMRNET",), within_miles=(HOME[0], HOME[1], 60.0))
    block = PlanBlock(label="DMR", selectors=(selector,), sort=SORT_TIER_DISTANCE)
    resolved = resolve_plan(_plan("at-d890uv", block), catalog, get_profile("at-d890uv"))
    assert [c.label for c in resolved.channels] == ["near-core", "far-core", "near-wide", "near-test"]


def test_dmr_tier_selector_splits_core_from_wide():
    core = ChannelSelector(favorite_keys=("X",), dmr_tiers=(0, 1))
    assert not core.is_empty()
    wa = Channel(id="a", label="a", freq_mhz=440.0, mode="DMR", dmr_talkgroup=3153, dmr_talkgroup_name="Washington 1", network="PNWDigital")
    idaho = Channel(id="b", label="b", freq_mhz=440.0, mode="DMR", dmr_talkgroup=3116, dmr_talkgroup_name="Idaho 1", network="PNWDigital")
    assert core.matches("X", "d", wa) and not core.matches("X", "d", idaho)


# ------------------------------------------------------- RadioReference ----
def _rr_king() -> FavoritesList:
    dispatch = Department(
        id="kcso", label="King County Sheriff", lat=47.49, lon=-121.84, range_miles=35.0,
        channels=[
            Channel(id="kc1", label="KCSO Tac", freq_mhz=155.550, mode="FM", service_type=7),
            Channel(id="kc2", label="KCSO P25", freq_mhz=155.610, mode="P25", service_type=2),
        ],
    )
    favorite = _favorite("RRC-KING", [dispatch])
    favorite.licensed = True
    return favorite


def test_radioreference_county_lists_reach_every_fleet_plan():
    catalog = Catalog(favorites=[_rr_king()])
    for radio_id in ("td-h9", "ftx1", "th-d75", "at-d890uv"):
        resolved = resolve_plan(build_fleet_plan(radio_id), catalog, get_profile(radio_id))
        labels = {c.label: c.block for c in resolved.channels}
        assert labels.get("KCSO Tac") == "Public Safety Conventional", radio_id
        reasons = {d.label: d.reason for d in resolved.dropped}
        assert reasons.get("KCSO P25") == "unsupported-mode", radio_id


def test_a_distant_county_list_stays_out():
    favorite = _rr_king()
    department = favorite.systems[0].departments[0]
    department.lat, department.lon = 47.66, -117.43  # Spokane
    resolved = resolve_plan(build_fleet_plan("td-h9"), Catalog(favorites=[favorite]), get_profile("td-h9"))
    assert "KCSO Tac" not in {c.label for c in resolved.channels}
