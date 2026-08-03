import pytest

from wasds150.generate.quickkeys import next_available_flqk, used_flqks
from wasds150.models.catalog import FavoritesList


def _fl(slug, flqk=None):
    return FavoritesList(
        id=slug,
        slug=slug,
        favorite_key=slug.upper(),
        favorite_name=slug,
        region="",
        counties="",
        scenario="",
        source_type="",
        system_or_category="",
        sites_or_coverage="",
        departments_or_channels="",
        mode="",
        monitorability="",
        upgrade_required="",
        source_url="",
        notes="",
        flqk=flqk,
    )


def test_used_flqks_groups_by_key_allows_sharing():
    favorites = [_fl("a", flqk=9), _fl("b", flqk=9), _fl("c", flqk=None)]
    used = used_flqks(favorites)
    assert used == {9: ["a", "b"]}


def test_next_available_flqk_skips_used_and_reserved():
    favorites = [_fl("a", flqk=1), _fl("b", flqk=2)]
    assert next_available_flqk(favorites, start=1, end=5) == 3


def test_next_available_flqk_returns_none_when_full():
    favorites = [_fl(f"x{i}", flqk=i) for i in range(1, 5)]
    assert next_available_flqk(favorites, start=1, end=4) is None


def test_next_available_flqk_never_returns_reserved_keys():
    favorites = []
    result = next_available_flqk(favorites, start=0, end=1)
    # 0 is reserved; default allocator should skip it and return 1 (allowed
    # because caller explicitly widened the range to include 0).
    assert result == 1


def test_next_available_flqk_rejects_invalid_range():
    with pytest.raises(ValueError):
        next_available_flqk([], start=5, end=1)
    with pytest.raises(ValueError):
        next_available_flqk([], start=-1, end=10)
    with pytest.raises(ValueError):
        next_available_flqk([], start=1, end=200)
