"""Tone cells and document links from the online sources, as they appear live."""
import pytest

from wasds150.hpe.validation import tone_is_valid
from wasds150.sources.docwatch import discover_document_links
from wasds150.sources.iacc import parse_iacc_tone


@pytest.mark.parametrize(
    "cell,expected",
    [
        ("136.5 In 136.5 Out", ("TONE=C136.5", "TONE=C136.5")),
        ("156.7 In 100.0 Out", ("TONE=C100", "TONE=C156.7")),
        ("100.0 In", ("", "TONE=C100")),
        ("123.0", ("", "TONE=C123")),
        ("D023 In D023 Out", ("D023", "D023")),
        ("Closed System", ("", "")),
        ("Private System", ("", "")),
        ("", ("", "")),
    ],
)
def test_iacc_tone_cells_decode_to_catalog_notation(cell, expected):
    assert parse_iacc_tone(cell) == expected
    for tone in expected:
        assert not tone or tone_is_valid(tone)


def test_flat_facts_never_carry_an_unparseable_tone_into_the_catalog():
    from wasds150.models.catalog import CSV_FIELDS, FavoritesList
    from wasds150.recipes.systems import systems_from_flat_facts
    from wasds150.sources.facts import NormalizedFact

    row = {name: "" for name in CSV_FIELDS}
    row.update(favorite_key="FLX", favorite_name="Test")
    fl = FavoritesList.from_csv_row(row)
    facts = [
        NormalizedFact(entity_key="a", fact_type="coordination", name="Good", freq_mhz=146.9,
                       tone="TONE=C103.5", mode="FM", source_id="iacc"),
        NormalizedFact(entity_key="b", fact_type="coordination", name="Bad", freq_mhz=147.1,
                       tone="136.5 In 136.5 Out", mode="FM", source_id="iacc"),
    ]
    channels = {c.label: c for c in systems_from_flat_facts(fl, facts)[0].departments[0].channels}
    assert channels["Good"].tone == "TONE=C103.5"
    assert channels["Bad"].tone == ""


def test_radioreference_text_with_line_breaks_becomes_one_line():
    from wasds150.hpe.validation import validate_favorites_list
    from wasds150.recipes.rr_county import RR_SOURCE_IDS, build_rr_favorites
    from wasds150.sources.facts import NormalizedFact

    fact = NormalizedFact(
        entity_key="rr:1", fact_type="frequency", name="Seattle PD\tOps\r\n1", freq_mhz=460.1,
        mode="FM", county="King", source_id=sorted(RR_SOURCE_IDS)[0],
        raw={"rr_category": "Law\nDispatch"},
    )
    fl = build_rr_favorites([fact])[0]
    department = fl.systems[0].departments[0]
    assert department.label == "Law Dispatch"
    assert department.channels[0].label == "Seattle PD Ops 1"
    assert not [i for i in validate_favorites_list(fl) if i.code == "unsafe-text"]


def test_the_scanner_is_handed_only_what_it_can_tune(tmp_path):
    # The Sentinel installer used to receive HAM01 unprojected and fail on its
    # 1.81 MHz CW record, though the .hpe export had projected it away.
    from wasds150.appctx import build_context
    from wasds150.config import AppConfig
    from wasds150.fleet.service import scanner_favorites

    config = AppConfig(home=tmp_path)
    config.ensure_dirs()
    favorites = scanner_favorites(build_context(config))
    keys = {favorite.favorite_key for favorite in favorites}
    assert {"HAM01", "HFNET01"} <= keys
    for favorite in favorites:
        for system in favorite.systems:
            for department in system.departments:
                for channel in department.channels:
                    if channel.freq_mhz is not None:
                        assert channel.freq_mhz >= 25.0, (favorite.favorite_key, channel.label)
                    assert (channel.mode or "").upper() not in {"CW", "USB", "LSB"}, (favorite.favorite_key, channel.label)


def test_document_links_with_spaces_are_percent_encoded():
    html = '<a href="/asset/66aa9c99701cb/SIEC Members.pdf">Members</a>'
    links = discover_document_links(html, base_url="https://mil.wa.gov/siec", pattern="/asset/")
    assert links == ["https://mil.wa.gov/asset/66aa9c99701cb/SIEC%20Members.pdf"]


def test_one_unfetchable_document_does_not_fail_the_others():
    from types import SimpleNamespace

    from wasds150.sources.docwatch import check_document_links

    class Client:
        store = SimpleNamespace(get=lambda url: None)

        def fetch(self, url, **_kwargs):
            if "big" in url:
                raise RuntimeError("response exceeded the byte limit while streaming; aborted")
            return SimpleNamespace(status="fetched")

    alerts = check_document_links(Client(), ["https://x.test/big.pdf", "https://x.test/ok.pdf"],
                                  source_id="wa_emd", ttl_seconds=60)
    assert [(a.url.rsplit("/", 1)[-1], a.kind) for a in alerts] == [("big.pdf", "unreachable"), ("ok.pdf", "new")]


def test_already_encoded_links_are_left_alone():
    html = '<a href="/asset/abc/SIEC%20Members.pdf?x=1&amp;y=2">Members</a>'
    links = discover_document_links(html, base_url="https://mil.wa.gov/siec", pattern="/asset/")
    assert links[0].startswith("https://mil.wa.gov/asset/abc/SIEC%20Members.pdf?x=1")
    assert "%25" not in links[0]
