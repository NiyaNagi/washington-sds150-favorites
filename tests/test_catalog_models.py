from wasds150.models.catalog import Catalog, FavoritesList, ORIGIN_BASELINE, ORIGIN_LOCAL
from wasds150.models.provenance import Provenance


def _make_fl(**overrides) -> FavoritesList:
    base = dict(
        id="id-1",
        slug="fl01",
        favorite_key="FL01",
        favorite_name="Alpha",
        region="Statewide",
        counties="All",
        scenario="Public safety",
        source_type="conventional",
        system_or_category="Alpha Net",
        sites_or_coverage="Statewide",
        departments_or_channels="ALPHA1",
        mode="FM",
        monitorability="Full",
        upgrade_required="None",
        source_url="https://example.org",
        notes="",
    )
    base.update(overrides)
    return FavoritesList(**base)


def test_from_csv_row_and_csv_row_round_trip():
    row = {
        "favorite_key": "FL01",
        "favorite_name": "Alpha",
        "region": "Statewide",
        "counties": "All",
        "scenario": "Public safety",
        "source_type": "conventional",
        "system_or_category": "Alpha Net",
        "sites_or_coverage": "Statewide",
        "departments_or_channels": "ALPHA1",
        "mode": "FM",
        "monitorability": "Full",
        "upgrade_required": "None",
        "source_url": "https://example.org",
        "notes": "",
    }
    fl = FavoritesList.from_csv_row(row)
    assert fl.slug == "fl01"
    assert fl.origin == ORIGIN_BASELINE
    assert fl.csv_row() == row


def test_to_dict_from_dict_round_trip():
    fl = _make_fl(provenance=[Provenance(source_adapter="static_pack", source_url="https://x")])
    data = fl.to_dict()
    restored = FavoritesList.from_dict(data)
    assert restored == fl


def test_content_hash_stable_and_sensitive():
    fl1 = _make_fl()
    fl2 = _make_fl()
    assert fl1.content_hash() == fl2.content_hash()

    fl3 = _make_fl(notes="different")
    assert fl1.content_hash() != fl3.content_hash()

    fl4 = _make_fl(enabled=False)
    assert fl1.content_hash() != fl4.content_hash()


def test_content_hash_ignores_id_and_provenance_object_identity():
    fl1 = _make_fl(id="id-1", provenance=[Provenance(source_adapter="static_pack")])
    fl2 = _make_fl(id="id-2", provenance=[Provenance(source_adapter="static_pack", fetched_at="2020")])
    # id and provenance timestamps are not part of the content hash payload.
    assert fl1.content_hash() == fl2.content_hash()


def test_catalog_content_hash_depends_on_list_order():
    a = _make_fl(slug="fl01", favorite_key="FL01")
    b = _make_fl(slug="fl02", favorite_key="FL02", notes="b")
    cat1 = Catalog(favorites=[a, b])
    cat2 = Catalog(favorites=[b, a])
    # Catalog.content_hash() is order-sensitive by design (it hashes the
    # favorites list as constructed); wasds150.generate.determinism is what
    # provides an order-independent, deterministically-sorted hash for
    # generated output. See tests/test_determinism.py.
    assert cat1.content_hash() != cat2.content_hash()

    cat3 = Catalog(favorites=[a, b])
    assert cat1.content_hash() == cat3.content_hash()


def test_catalog_by_slug():
    a = _make_fl(slug="fl01")
    b = _make_fl(slug="fl02", favorite_key="FL02")
    cat = Catalog(favorites=[a, b])
    assert cat.by_slug("fl02") is b
    assert cat.by_slug("missing") is None


def test_local_origin_marker():
    fl = _make_fl(origin=ORIGIN_LOCAL)
    assert fl.origin == ORIGIN_LOCAL
