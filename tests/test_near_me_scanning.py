"""How a Near Me list is chosen on the memory radios: pinned repeaters first,
then the nearest reachable stations, never one known to be out of reach, DMR by
talkgroup tier - and listed by frequency."""
from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import SORT_NEAREST, ChannelPlan, ChannelSelector, PlanBlock, ScanGroup
from wasds150.plan.resolve import PlannedChannel, resolve_plan
from wasds150.plan.scanning import group_members


def _ch(name, mhz, block="Nets", *, miles=None, tx=None, rank=0, tier=0, skip=False):
    return PlannedChannel(slot=0, name=name, label=name, rx_freq_mhz=mhz, mode="FM", block=block, source="t",
                          transmit=True, tx_freq_mhz=tx, distance_miles=miles, rank=rank, tier=tier, skip_scan=skip)


def test_pinned_first_then_nearest_within_reach_and_listed_by_frequency():
    group = ScanGroup("Near Me", ("Nets", "Ham 2m"), take=(("Nets", 2), ("Ham 2m", 2)),
                      pinned=((146.96, "WW7PSR"), (443.05, "KC7BAE")), reach_miles=35.0, frequency_order=True)
    channels = [
        _ch("W7DX Union Hill", 147.00, miles=6.0, tx=146.40, rank=0),
        _ch("N7SK Shelton", 146.72, miles=58.0, tx=146.12, rank=1),
        _ch("WW7PSR Seattle", 146.96, miles=22.0, tx=146.36, rank=2),
        _ch("KC7BAE E Tiger", 443.05, miles=9.0, tx=448.05, rank=3),
        _ch("Far 2m", 145.49, "Ham 2m", miles=40.0, tx=144.89),
        _ch("Near 2m", 147.08, "Ham 2m", miles=12.0, tx=147.68),
        _ch("Simplex", 146.58, "Ham 2m"),  # no site: after the known-near, never instead of them
    ]
    members = group_members(group, channels)
    # Both pinned nets beat the nearer W7DX; Shelton and the 40-mile 2 m machine are out of reach.
    assert [c.name for c in members] == ["Simplex", "WW7PSR Seattle", "Near 2m", "KC7BAE E Tiger"]


def test_a_pinned_repeater_is_kept_beyond_reach_and_a_scan_locked_row_never_is():
    group = ScanGroup("Near Me", ("Nets",), take=(("Nets", 1),), pinned=((146.72, "N7SK"),), reach_miles=35.0)
    channels = [
        _ch("W7DX Union Hill", 147.00, miles=6.0, tx=146.40),
        _ch("N7SK Shelton", 146.72, miles=58.0, tx=146.12),
        _ch("Locked", 146.50, miles=1.0, tx=145.90, skip=True),
    ]
    assert [c.name for c in group_members(group, channels)] == ["N7SK Shelton"]


def test_a_dmr_quota_takes_calling_talkgroups_before_nearer_wide_area_ones():
    group = ScanGroup("Near Me", ("DMR",), take=(("DMR", 1),), reach_miles=35.0)
    channels = [
        _ch("Wide TG near", 440.775, "DMR", miles=5.0, tx=445.775, tier=2),
        _ch("Local TG farther", 442.325, "DMR", miles=20.0, tx=447.325, tier=0),
    ]
    assert [c.name for c in group_members(group, channels)] == ["Local TG farther"]


def test_a_fleet_plan_lists_each_block_by_frequency_but_keeps_its_nearest():
    department = Department(id="d", label="Ham", channels=[
        Channel(id="a", label="Near high", freq_mhz=147.30, tx_freq_mhz=147.90, mode="FM", lat=47.64, lon=-121.97),
        Channel(id="b", label="Mid", freq_mhz=146.00, tx_freq_mhz=146.60, mode="FM", lat=47.70, lon=-122.20),
        Channel(id="c", label="Far low", freq_mhz=145.11, tx_freq_mhz=144.51, mode="FM", lat=48.40, lon=-122.90),
    ])
    favorite = FavoritesList(
        id="f", slug="ham", favorite_key="HAM", favorite_name="Ham", region="", counties="", scenario="",
        source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
        monitorability="", upgrade_required="", source_url="", notes="",
        systems=[System(id="s", label="S", departments=[department])],
    )
    plan = ChannelPlan(
        id="t", radio_id="td-h9", label="t", home=(47.634, -121.96), frequency_order=True,
        blocks=(PlanBlock("Ham 2m", (ChannelSelector(favorite_keys=("HAM",)),), sort=SORT_NEAREST, limit=2),),
    )
    resolved = resolve_plan(plan, Catalog(favorites=[favorite]))
    # The two nearest are kept (the far one is not), then listed low to high.
    assert [(c.slot, c.label, c.rank) for c in resolved.channels] == [(1, "Mid", 1), (2, "Near high", 0)]
