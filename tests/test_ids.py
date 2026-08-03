import pytest

from wasds150.catalog.ids import natural_sort_key, slugify, stable_id


def test_slugify_lowercases_and_strips():
    assert slugify("  FL09a  ") == "fl09a"
    assert slugify("LOCAL01") == "local01"


def test_natural_sort_key_orders_numerically_not_lexically():
    keys = ["FL10", "FL2", "FL1", "FL9a", "FL9b", "FL9"]
    ordered = sorted(keys, key=natural_sort_key)
    assert ordered == ["FL1", "FL2", "FL9", "FL9a", "FL9b", "FL10"]


def test_natural_sort_key_handles_unrecognized_keys_after_recognized_ones():
    keys = ["FL02", "LOCAL_B", "FL01", "LOCAL_A"]
    ordered = sorted(keys, key=natural_sort_key)
    assert ordered == ["FL01", "FL02", "LOCAL_A", "LOCAL_B"]


def test_stable_id_matches_catalog_ids_helper():
    from wasds150.util.hashing import stable_id as util_stable_id

    assert stable_id("fl01") == util_stable_id("fl01")
