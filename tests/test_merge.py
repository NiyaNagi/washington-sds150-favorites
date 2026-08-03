from wasds150.merge.conflicts import MergeConflict
from wasds150.merge.keys import FACT_FIELDS, PRESENTATION_FIELDS, classify_field, is_fact_field, is_presentation_field
from wasds150.merge.three_way import apply_merge, three_way_merge
from wasds150.models.catalog import Catalog, FavoritesList
from wasds150.models.profile import Profile


def _fl(slug, name="Name", notes="notes", **overrides):
    base = dict(
        id=slug, slug=slug, favorite_key=slug.upper(), favorite_name=name, region="r", counties="c",
        scenario="s", source_type="t", system_or_category="sc", sites_or_coverage="site",
        departments_or_channels="d", mode="FM", monitorability="full", upgrade_required="none",
        source_url="u", notes=notes,
    )
    base.update(overrides)
    return FavoritesList(**base)


# ------------------------------------------------------------------ keys --
def test_fact_fields_exclude_notes():
    assert "notes" not in FACT_FIELDS
    assert "favorite_name" in FACT_FIELDS


def test_presentation_fields_are_notes_flqk_enabled():
    assert set(PRESENTATION_FIELDS) == {"notes", "flqk", "enabled"}


def test_classify_field():
    assert classify_field("favorite_name") == "fact"
    assert classify_field("notes") == "presentation"
    assert classify_field("flqk") == "presentation"


def test_classify_field_unknown_raises():
    import pytest

    with pytest.raises(ValueError):
        classify_field("not_a_real_field")


def test_is_fact_and_is_presentation_helpers():
    assert is_fact_field("region")
    assert not is_fact_field("notes")
    assert is_presentation_field("flqk")
    assert not is_presentation_field("region")


# ------------------------------------------------------------ conflicts ---
def test_merge_conflict_to_dict():
    c = MergeConflict(slug="fl01", field="favorite_name", base_value="A", upstream_value="B", local_value="C")
    d = c.to_dict()
    assert d == {
        "slug": "fl01", "field": "favorite_name", "base_value": "A",
        "upstream_value": "B", "local_value": "C", "label": "",
    }


# --------------------------------------------------------------- engine ---
def test_no_upstream_changes_produces_no_changes_or_conflicts():
    base = Catalog(favorites=[_fl("fl01")])
    upstream = Catalog(favorites=[_fl("fl01")])
    result = three_way_merge(base, upstream, Profile())
    assert result.changes == []
    assert result.conflicts == []
    assert not result.has_conflicts


def test_fact_field_change_with_no_local_override_auto_updates():
    base = Catalog(favorites=[_fl("fl01", name="Old")])
    upstream = Catalog(favorites=[_fl("fl01", name="New")])
    result = three_way_merge(base, upstream, Profile())
    assert len(result.changes) == 1
    change = result.changes[0]
    assert change.op == "updated"
    assert change.field == "favorite_name"
    assert change.before == "Old"
    assert change.after == "New"
    assert result.conflicts == []


def test_fact_field_change_with_matching_local_override_is_not_a_conflict():
    base = Catalog(favorites=[_fl("fl01", name="Old")])
    upstream = Catalog(favorites=[_fl("fl01", name="New")])
    profile = Profile()
    profile.set_override("fl01", "favorite_name", "New")  # already matches upstream
    result = three_way_merge(base, upstream, profile)
    assert result.conflicts == []
    assert len(result.changes) == 1
    assert result.changes[0].op == "updated"


def test_fact_field_change_with_disagreeing_local_override_is_a_conflict():
    base = Catalog(favorites=[_fl("fl01", name="Old")])
    upstream = Catalog(favorites=[_fl("fl01", name="New")])
    profile = Profile()
    profile.set_override("fl01", "favorite_name", "My Custom Name")
    result = three_way_merge(base, upstream, profile)
    assert result.changes == []
    assert len(result.conflicts) == 1
    conflict = result.conflicts[0]
    assert conflict.slug == "fl01"
    assert conflict.field == "favorite_name"
    assert conflict.base_value == "Old"
    assert conflict.upstream_value == "New"
    assert conflict.local_value == "My Custom Name"
    assert result.has_conflicts


def test_presentation_field_never_conflicts_even_with_override():
    # notes differs between base and upstream, but notes is a presentation
    # field: upstream never "owns" it, so no conflict/change is ever raised
    # for it regardless of local override state.
    base = Catalog(favorites=[_fl("fl01", notes="base notes")])
    upstream = Catalog(favorites=[_fl("fl01", notes="upstream notes")])
    profile = Profile()
    profile.set_override("fl01", "notes", "my note")
    result = three_way_merge(base, upstream, profile)
    assert result.changes == []
    assert result.conflicts == []


def test_removed_slug_reported():
    base = Catalog(favorites=[_fl("fl01"), _fl("fl02")])
    upstream = Catalog(favorites=[_fl("fl01")])
    result = three_way_merge(base, upstream, Profile())
    removed = [c for c in result.changes if c.op == "removed"]
    assert len(removed) == 1
    assert removed[0].slug == "fl02"


def test_added_slug_reported():
    base = Catalog(favorites=[_fl("fl01")])
    upstream = Catalog(favorites=[_fl("fl01"), _fl("fl02")])
    result = three_way_merge(base, upstream, Profile())
    added = [c for c in result.changes if c.op == "added"]
    assert len(added) == 1
    assert added[0].slug == "fl02"


def test_merged_catalog_equals_upstream():
    base = Catalog(favorites=[_fl("fl01", name="Old")])
    upstream = Catalog(favorites=[_fl("fl01", name="New"), _fl("fl02")])
    result = three_way_merge(base, upstream, Profile())
    assert [fl.slug for fl in result.merged_catalog.favorites] == ["fl01", "fl02"]
    assert result.merged_catalog.by_slug("fl01").favorite_name == "New"


# ------------------------------------------------------------ apply_merge -
def test_apply_merge_repins_catalog_hash():
    base = Catalog(favorites=[_fl("fl01")])
    upstream = Catalog(favorites=[_fl("fl01", name="New")])
    profile = Profile(based_on_catalog_hash=base.content_hash())
    result = three_way_merge(base, upstream, profile)
    new_profile = apply_merge(profile, result)
    assert new_profile.based_on_catalog_hash == result.merged_catalog.content_hash()
    assert new_profile.based_on_catalog_hash != base.content_hash()


def test_apply_merge_prunes_orphaned_overrides_for_removed_slugs():
    base = Catalog(favorites=[_fl("fl01"), _fl("fl02")])
    upstream = Catalog(favorites=[_fl("fl01")])  # fl02 removed upstream
    profile = Profile()
    profile.set_enabled("fl02", False)
    profile.set_override("fl01", "notes", "keep me")

    result = three_way_merge(base, upstream, profile)
    new_profile = apply_merge(profile, result)

    assert "fl02" not in new_profile.entries  # pruned: no longer a valid baseline slug
    assert "fl01" in new_profile.entries  # preserved: still valid
    assert new_profile.entries["fl01"].overrides["notes"] == "keep me"


def test_apply_merge_preserves_local_lists_untouched():
    base = Catalog(favorites=[_fl("fl01")])
    upstream = Catalog(favorites=[_fl("fl01")])
    profile = Profile()
    local_fl = _fl("mylocal01", name="My Local")
    profile.local_lists["mylocal01"] = local_fl

    result = three_way_merge(base, upstream, profile)
    new_profile = apply_merge(profile, result)
    assert new_profile.local_lists["mylocal01"] == local_fl  # untouched by merge


def test_apply_merge_leaves_conflicting_override_value_unchanged():
    base = Catalog(favorites=[_fl("fl01", name="Old")])
    upstream = Catalog(favorites=[_fl("fl01", name="New")])
    profile = Profile()
    profile.set_override("fl01", "favorite_name", "My Custom Name")

    result = three_way_merge(base, upstream, profile)
    assert result.has_conflicts
    new_profile = apply_merge(profile, result)
    # The conflicting override is preserved exactly as-is; merge never
    # silently discards or silently forces a resolution.
    assert new_profile.entries["fl01"].overrides["favorite_name"] == "My Custom Name"
