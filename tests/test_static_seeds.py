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


def test_npspac_seed_applies_when_anchors_present():
    text = "ICALL 866.0125; ITAC1-4 866.5125-868.0125; STATEOPS1-5 867.5375-867.6375 (Fire/EMS/Law/LocalGov)"
    channels = seed_channels_for("FL02", text)
    labels = {c.label: c.freq_mhz for c in channels}
    assert labels == {
        "ICALL": 866.0125,
        "ITAC1": 866.5125,
        "ITAC2": 867.0125,
        "ITAC3": 867.5125,
        "ITAC4": 868.0125,
    }


def test_npspac_seed_never_seeds_state_specific_stateops():
    text = "ICALL 866.0125; ITAC1-4 866.5125-868.0125; STATEOPS1-5 867.5375-867.6375"
    channels = seed_channels_for("FL02", text)
    assert not any("STATEOPS" in c.label for c in channels)


def test_seed_does_not_fire_for_unrelated_row_reusing_the_same_key():
    """The safety-critical case: a favorite_key collision (e.g. a
    different/local/test catalog reusing "FL02") must never pull in the
    NPSPAC seed unless the row's own text actually contains the anchors."""
    channels = seed_channels_for("FL02", "Bravo Dispatch, [E]-ENCRYPTED")
    assert channels == []


def test_seed_does_not_fire_for_unknown_favorite_key():
    assert seed_channels_for("FL99", "462.5625-462.7125") == []


def test_seed_requires_all_anchors_not_just_one():
    # Only one of the three FRS/GMRS anchors present -- must not partially
    # apply the seed table.
    assert seed_channels_for("FL65", "462.5625 only, nothing else") == []


def test_seed_channels_for_returns_fresh_list_each_time():
    text = "ICALL 866.0125; ITAC1-4 866.5125-868.0125"
    a = seed_channels_for("FL02", text)
    b = seed_channels_for("FL02", text)
    assert a is not b
    a.append(a[0])
    assert len(seed_channels_for("FL02", text)) == 5  # unaffected by mutating `a`


def test_seed_channels_convert_to_conventional_channels_never_talkgroups():
    """These are public conventional/simplex channel plans, never trunked
    talkgroups -- the explicit thing the audit said must never be
    fabricated. Confirmed at the point they actually matter: once
    converted into catalog Channel objects (see
    wasds150.recipes.systems), none carry a tgid."""
    from wasds150.recipes.systems import _channel_from_parsed

    text_frs = "Ch1-7 shared462.5625-462.7125;Ch8-14 FRS-only467.5625-467.7125;Ch15-22 GMRS/FRS462.5500-462.7250"
    text_npspac = "ICALL 866.0125; ITAC1-4 866.5125-868.0125"
    parsed = seed_channels_for("FL65", text_frs) + seed_channels_for("FL02", text_npspac)
    channels = [_channel_from_parsed("slug", i, p) for i, p in enumerate(parsed)]
    assert channels  # sanity: the seeds actually produced something
    assert all(c.tgid is None for c in channels)
    assert all(c.freq_mhz is not None for c in channels)

