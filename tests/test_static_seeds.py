"""Tests for the hand-curated national public channel-plan seed tables
(see module docstring for why each table is safe to hand-author)."""
from __future__ import annotations

from wasds150.sources.static_seeds import seed_channels_for


def test_frs_gmrs_seed_applies_when_anchors_present():
    text = "Ch1-7 shared462.5625-462.7125;Ch8-14 FRS-only467.5625-467.7125(0.5W);Ch15-22 GMRS/FRS462.5500-462.7250"
    channels = seed_channels_for("FL65", text)
    assert len(channels) == 7 + 7 + 8
    freqs = sorted(c.freq_mhz for c in channels)
    assert freqs[0] == 462.55
    assert freqs[-1] == 467.7125


def test_frs_gmrs_seed_channel_1_and_22_match_baseline_endpoints():
    text = "Ch1-7 shared462.5625-462.7125;Ch8-14 FRS-only467.5625-467.7125(0.5W);Ch15-22 GMRS/FRS462.5500-462.7250"
    channels = seed_channels_for("FL65", text)
    by_label = {c.label: c.freq_mhz for c in channels}
    assert by_label["FRS/GMRS Ch1"] == 462.5625
    assert by_label["FRS/GMRS Ch7"] == 462.7125
    assert by_label["FRS Ch8"] == 467.5625
    assert by_label["FRS Ch14"] == 467.7125
    assert by_label["GMRS/FRS Ch15"] == 462.5500
    assert by_label["GMRS/FRS Ch22"] == 462.7250


def test_current_nifog_wafog_seed_applies_when_anchors_present():
    text = "VCALL10 155.7525;7CALL50 769.24375;8CALL90 851.0125;STATEOPS1 852.5375"
    channels = seed_channels_for("FL02", text)
    labels = {c.label: c.freq_mhz for c in channels}
    assert len(labels) == 24
    assert labels["VCALL10"] == 155.7525
    assert labels["UCALL40"] == 453.2125
    assert labels["7CALL50"] == 769.24375
    assert labels["8CALL90"] == 851.0125
    assert labels["8TAC94"] == 853.0125
    assert labels["STATEOPS5"] == 852.6375
    assert all(c.tone == "CTCSS 156.7" for c in channels if not c.label.startswith("7"))


def test_obsolete_pre_rebanding_npspac_does_not_trigger_current_seed():
    text = "ICALL 866.0125;ITAC1 866.5125;ITAC4 868.0125"
    assert seed_channels_for("FL02", text) == []


def test_seed_does_not_fire_for_unrelated_row_reusing_the_same_key():
    """The safety-critical case: a favorite_key collision (e.g. a
    different/local/test catalog reusing "FL02") must never pull in the
    NIFOG seed unless the row's own text actually contains the anchors."""
    channels = seed_channels_for("FL02", "Bravo Dispatch, [E]-ENCRYPTED")
    assert channels == []


def test_seed_does_not_fire_for_unknown_favorite_key():
    assert seed_channels_for("FL99", "462.5625-462.7125") == []


def test_seed_requires_all_anchors_not_just_one():
    # Only one of the three FRS/GMRS anchors present -- must not partially
    # apply the seed table.
    assert seed_channels_for("FL65", "462.5625 only, nothing else") == []


def test_seed_channels_for_returns_fresh_list_each_time():
    text = "VCALL10 155.7525;7CALL50 769.24375;8CALL90 851.0125;STATEOPS1 852.5375"
    a = seed_channels_for("FL02", text)
    b = seed_channels_for("FL02", text)
    assert a is not b
    a.append(a[0])
    assert len(seed_channels_for("FL02", text)) == 24  # unaffected by mutating `a`


def test_seed_channels_convert_to_conventional_channels_never_talkgroups():
    """These are public conventional/simplex channel plans, never trunked
    talkgroups -- the explicit thing the audit said must never be
    fabricated. Confirmed at the point they actually matter: once
    converted into catalog Channel objects (see
    wasds150.recipes.systems), none carry a tgid."""
    from wasds150.models.catalog import FavoritesList
    from wasds150.recipes.systems import _channel_from_parsed

    text_frs = "Ch1-7 shared462.5625-462.7125;Ch8-14 FRS-only467.5625-467.7125;Ch15-22 GMRS/FRS462.5500-462.7250"
    text_interop = "VCALL10 155.7525;7CALL50 769.24375;8CALL90 851.0125;STATEOPS1 852.5375"
    parsed = seed_channels_for("FL65", text_frs) + seed_channels_for("FL02", text_interop)
    fl = FavoritesList(
        id="slug", slug="slug", favorite_key="TEST", favorite_name="Test",
        region="", counties="", scenario="", source_type="", system_or_category="",
        sites_or_coverage="", departments_or_channels="", mode="FM",
        monitorability="", upgrade_required="", source_url="", notes="",
    )
    channels = [_channel_from_parsed(fl, i, p) for i, p in enumerate(parsed)]
    assert channels  # sanity: the seeds actually produced something
    assert all(c.tgid is None for c in channels)
    assert all(c.freq_mhz is not None for c in channels)


def test_cb_seed_preserves_non_linear_channel_order():
    channels = seed_channels_for("FL66", "CB Ch9 27.065;Ch19 27.185")
    by_label = {channel.label: channel.freq_mhz for channel in channels}
    assert len(channels) == 40
    assert by_label["CB Ch23"] == 27.255
    assert by_label["CB Ch24"] == 27.235
    assert by_label["CB Ch25"] == 27.245


def test_marine_seed_requires_row_specific_anchors():
    channels = seed_channels_for(
        "FL54",
        "Ch07A156.350;Ch05A156.250;Ch13/16/01A;Port of Seattle P25",
    )
    assert {channel.freq_mhz for channel in channels} == {156.05, 156.65, 156.8}
    assert seed_channels_for("FL54", "unrelated Ch16 list") == []
