"""Contact directories: radioid.net parsing, the store, CPS contact files."""
from __future__ import annotations

import csv
import io
from types import SimpleNamespace

import pytest

from conftest import REPO_CSV_PATH
from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.contacts.model import ContactStore, clean_ascii
from wasds150.contacts.radioid import RadioIdSource, parse_contacts
from wasds150.contacts.refresh import protocols_for_fleet, refresh_contacts
from wasds150.export.atd890_contacts import CONTACT_HEADER, contact_files, render_contact_csv
from wasds150.radios.profile import ContactCapability

SAMPLE = (
    "RADIO_ID,CALLSIGN,FIRST_NAME,LAST_NAME,CITY,STATE,COUNTRY\n"
    "3153001,ka7xyz,Pat,Lee,Redmond,Washington,United States\n"
    "2401234,SM0ÅBC,Åsa,Öberg,Göteborg,Västra Götaland,Sweden\n"
    '3100002,K1ABC,"Jo, ""Jr""",Smith|X,Boston,Massachusetts,United States\n'
    "not-a-number,BAD,,,,,\n"
    "3153001,DUPE,,,,,\n"
    "0,ZERO,,,,,\n"
)


class FakeHttp:
    def __init__(self, bodies):
        self.bodies = bodies
        self.calls = []

    def fetch(self, url, ttl_seconds=0, source_id=None, max_bytes=None):
        self.calls.append((url, source_id, max_bytes))
        return SimpleNamespace(content=self.bodies[url].encode("utf-8"))


def test_clean_ascii_folds_accents_and_drops_separators():
    assert clean_ascii("Åsa Öberg") == "Asa Oberg"
    assert clean_ascii('Jo, "Jr" |X') == "Jo Jr X"
    assert clean_ascii("東京 Tokyo") == "Tokyo"


def test_parsing_cleans_dedupes_and_skips_bad_rows():
    table = parse_contacts(SAMPLE, "dmr", source_url="u", retrieved_at="t")
    assert [c.radio_id for c in table.rows] == [3153001, 2401234, 3100002]
    pat, asa, jo = table.rows
    assert pat.callsign == "KA7XYZ" and pat.name == "Pat Lee"
    assert asa.callsign == "SM0ABC" and asa.name == "Asa Oberg" and asa.city == "Goteborg"
    assert jo.first_name == "Jo Jr" and jo.last_name == "SmithX"
    assert table.protocol == "DMR" and len(table.sha256) == 64


def test_nxdn_ids_are_sixteen_bit_and_headers_are_required():
    table = parse_contacts("RADIO_ID,CALLSIGN\n65000,A\n70000,B\n", "NXDN")
    assert [c.radio_id for c in table.rows] == [65000]
    with pytest.raises(ValueError):
        parse_contacts("ID,CALL\n1,A\n", "DMR")
    with pytest.raises(ValueError):
        parse_contacts("", "DMR")


def test_store_round_trip(tmp_path):
    store = ContactStore(tmp_path / "contacts")
    table = parse_contacts(SAMPLE, "DMR", source_url="https://radioid.net/static/user.csv", retrieved_at="2026-09-10")
    store.save(table)
    loaded = store.load("dmr")
    assert loaded.rows == table.rows
    assert loaded.sha256 == table.sha256
    assert store.meta()["DMR"]["rows"] == 3
    assert store.load("NXDN") is None


def test_contact_csv_is_private_calls_filled_by_header_name():
    rows = parse_contacts(SAMPLE, "DMR").rows
    parsed = list(csv.reader(io.StringIO(render_contact_csv(rows))))
    assert tuple(parsed[0]) == CONTACT_HEADER
    assert parsed[1][:4] == ["1", "3153001", "KA7XYZ", "Pat Lee"]
    assert {row[CONTACT_HEADER.index("Call Type")] for row in parsed[1:]} == {"Private Call"}
    reordered = list(csv.reader(io.StringIO(render_contact_csv(rows, header=("Callsign", "Radio ID")))))
    assert reordered[1] == ["KA7XYZ", "3153001"]


def test_contact_files_split_at_the_radio_limit_and_flag_the_unverified_format():
    table = parse_contacts(SAMPLE, "DMR")
    files, warnings = contact_files([table], ContactCapability(protocols=frozenset({"DMR"}), max_contacts=2))
    assert sorted(files) == ["DigitalContactList.CSV", "DigitalContactList_2.CSV"]
    assert any("exceed" in w for w in warnings)
    assert any("not yet confirmed" in w for w in warnings)
    none, _ = contact_files([table], ContactCapability(protocols=frozenset({"NXDN"}), max_contacts=10))
    assert none == {}


def test_radioid_source_fetches_both_lists_and_makes_no_catalog_facts():
    from wasds150.sources.factory import runnable_source_names

    source = RadioIdSource()
    http = FakeHttp({
        "https://radioid.net/static/user.csv": SAMPLE,
        "https://radioid.net/static/nxdn.csv": "RADIO_ID,CALLSIGN\n1234,KB7NXD\n",
    })
    raw = source.fetch(http)
    assert [c[1] for c in http.calls] == ["radioid", "radioid"]
    assert {t.protocol: len(t.rows) for t in source.tables(raw)} == {"DMR": 3, "NXDN": 1}
    assert source.normalize(raw).facts == []
    assert RadioIdSource.kind == "contacts" and RadioIdSource.bulk
    assert "radioid" not in runnable_source_names()


@pytest.fixture()
def ctx(tmp_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=REPO_CSV_PATH)


def test_refresh_stores_what_the_fleet_can_hold(ctx):
    assert protocols_for_fleet() == ("DMR", "NXDN")
    http = FakeHttp({
        "https://radioid.net/static/user.csv": SAMPLE,
        "https://radioid.net/static/nxdn.csv": "RADIO_ID,CALLSIGN\n1234,KB7NXD\n",
    })
    summary = refresh_contacts(ctx, http_client=http)
    assert summary == "DMR 3 contacts; NXDN 1 contacts"
    assert ContactStore(ctx.config.contacts_dir).load("NXDN").rows[0].callsign == "KB7NXD"


def test_fleet_export_puts_contacts_beside_the_bundle_but_not_in_the_manifest(ctx, tmp_path):
    from wasds150.fleet.service import export_radio

    without = export_radio(ctx, "at-d890uv", out_dir=tmp_path / "a")
    assert any("no DMR/NXDN contact list" in w for w in without.warnings)

    ContactStore(ctx.config.contacts_dir).save(parse_contacts(SAMPLE, "DMR"))
    export = export_radio(ctx, "at-d890uv", out_dir=tmp_path / "b", copy_to=tmp_path / "copy")
    contacts = export.path / "DigitalContactList.CSV"
    assert contacts.is_file() and contacts in export.files
    assert "DigitalContactList" not in (export.path / "at-d890uv-fleet.LST").read_text(encoding="ascii")
    assert (tmp_path / "copy" / "at-d890uv-fleet" / "DigitalContactList.CSV").is_file()
