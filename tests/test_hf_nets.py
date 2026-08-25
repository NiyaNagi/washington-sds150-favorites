"""The HF nets and utility reference list."""
from __future__ import annotations

import datetime

import pytest

from wasds150.catalog.hf_nets import FAVORITE_KEY, SLUG, favorites
from wasds150.catalog.puget_ham import coordination_expired


@pytest.fixture(scope="module")
def favorite():
    lists = favorites()
    assert len(lists) == 1
    return lists[0]


def _channels(favorite):
    for system in favorite.systems:
        for department in system.departments:
            for channel in department.channels:
                yield department, channel


# ------------------------------------------------------------- structure --
def test_identity(favorite):
    assert favorite.favorite_key == FAVORITE_KEY
    assert favorite.slug == SLUG


def test_is_reference_only(favorite):
    """Most of this list is below 25 MHz, which the SDS150 cannot hear.

    Without the flag, generation treats the dropped channels as an error
    rather than an expected projection.
    """
    assert favorite.reference_only is True


def test_department_and_channel_counts(favorite):
    departments = [d for d, _ in _channels(favorite)]
    assert len({d.label for d in departments}) == 8
    assert len(list(_channels(favorite))) == 54


def test_every_channel_has_a_frequency_and_mode(favorite):
    for _department, channel in _channels(favorite):
        assert channel.freq_mhz and channel.freq_mhz > 0, channel.label
        assert channel.mode, channel.label


def test_channel_ids_are_unique(favorite):
    ids = [c.id for _d, c in _channels(favorite)]
    assert len(ids) == len(set(ids))


def test_labels_are_unique_within_a_department(favorite):
    """Frequencies deliberately repeat - several nets share 14.300 at different
    hours - so the label is what has to distinguish them."""
    seen = set()
    for department, channel in _channels(favorite):
        key = (department.label, channel.label)
        assert key not in seen, f"duplicate {channel.label} in {department.label}"
        seen.add(key)


def test_shared_frequencies_are_kept_as_separate_entries(favorite):
    """Collapsing them would lose the net identity and its schedule note."""
    on_14300 = [c.label for _d, c in _channels(favorite) if round(c.freq_mhz, 4) == 14.300]
    assert len(on_14300) > 1


def test_the_list_carries_provenance(favorite):
    assert favorite.provenance
    for entry in favorite.provenance:
        assert entry.confidence in ("verified", "community", "derived")
        assert entry.source_url


def test_every_channel_explains_itself(favorite):
    """A bare frequency in a scanner list is useless without knowing what it is."""
    for _department, channel in _channels(favorite):
        assert channel.notes.strip(), channel.label


# ---------------------------------------------------------------- content --
def test_covers_the_bands_the_user_asked_for(favorite):
    """160m through 6m."""
    freqs = [c.freq_mhz for _d, c in _channels(favorite)]
    assert min(freqs) < 4.0, "expected 160m/80m content"
    assert any(50.0 <= f <= 54.0 for f in freqs), "expected 6m content"


def test_known_anchor_frequencies_are_present(favorite):
    freqs = {round(c.freq_mhz, 4) for _d, c in _channels(favorite)}
    for expected in (
        14.300,  # Maritime Mobile Service Net
        14.325,  # Hurricane Watch Net
        14.100,  # NCDXF beacons
        10.000,  # WWV
        50.125,  # 6m SSB calling
    ):
        assert expected in freqs, f"missing {expected} MHz"


def test_scheduled_nets_warn_that_schedules_move(favorite):
    """Frequencies are stable, net times are not. Saying so avoids a false
    expectation that the radio will hear traffic at any given moment."""
    scheduled = [
        c
        for d, c in _channels(favorite)
        if "Net" in d.label or "Nets" in d.label
    ]
    assert scheduled
    for channel in scheduled:
        assert "confirm with the net" in channel.notes.lower(), channel.label


def test_beacon_and_standard_departments_exist(favorite):
    labels = {d.label for d, _c in _channels(favorite)}
    assert "HF Propagation Beacons" in labels
    assert "Time and Frequency Standards" in labels


# --------------------------------------------------- expiry classification --
TODAY = datetime.date(2026, 8, 24)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2027-01-01", False),
        ("2026-08-25", False),
        ("2026-08-24", False),  # expires at end of day
        ("2026-08-23", True),
        ("2020-01-01", True),
    ],
)
def test_coordination_expiry(raw, expected):
    assert coordination_expired({"EXPIRATION_DATE": raw}, today=TODAY) is expected


@pytest.mark.parametrize("raw", ["", "   ", None, "not a date", "0000-00-00"])
def test_unreadable_expiry_is_treated_as_current(raw):
    """Hiding a repeater because its date field is malformed is the worse
    failure; an unusable listing is more obvious to the user than a missing one."""
    assert coordination_expired({"EXPIRATION_DATE": raw}, today=TODAY) is False


def test_missing_expiry_field_is_treated_as_current():
    assert coordination_expired({}, today=TODAY) is False

