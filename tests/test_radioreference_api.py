"""RadioReference web-service connector.

The fixtures copy the service's RPC/encoded response shape (as returned live
by getCountryList) with made-up values, so no licensed data is committed and
no test touches the network.
"""
from __future__ import annotations

import pytest

from wasds150.hpe.validation import validate_favorites_list
from wasds150.models.catalog import CSV_FIELDS, Catalog, Channel, Department, FavoritesList, Site, System, TrunkFrequency
from wasds150.recipes.default_recipes import build_default_recipes
from wasds150.recipes.engine import enrich_catalog
from wasds150.recipes.systems import refresh_trunk_frequencies
from wasds150.sources.config import SourcesConfig
from wasds150.sources.facts import NormalizedFact
from wasds150.sources.factory import instantiate_source
from wasds150.sources.radioreference_api import (
    PASSWORD_ENV,
    USERNAME_ENV,
    RadioReferenceApi,
    RadioReferenceApiError,
    RadioReferenceApiSource,
    catalog_system_ids,
    resolve_credentials,
    system_from_api,
)
from wasds150.sources.radioreference_premium import RadioReferenceCredentials

ENVELOPE = (
    '<?xml version="1.0" encoding="utf-8"?><SOAP-ENV:Envelope '
    'xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
    'xmlns:tns="http://api.radioreference.com/soap2"><SOAP-ENV:Body>{body}</SOAP-ENV:Body></SOAP-ENV:Envelope>'
)


def _response(op, value):
    return ENVELOPE.format(body=f'<ns1:{op}Response xmlns:ns1="http://api.radioreference.com/soap2">{value}</ns1:{op}Response>')


def _i(name, value):
    return f'<{name} xsi:type="xsd:int">{value}</{name}>'


def _s(name, value):
    return f'<{name} xsi:type="xsd:string">{value}</{name}>'


def _d(name, value):
    return f'<{name} xsi:type="xsd:decimal">{value}</{name}>'


def _array(name, type_, items):
    inner = "".join(f'<item xsi:type="tns:{type_}">{item}</item>' for item in items)
    return f'<{name} xsi:type="SOAP-ENC:Array" SOAP-ENC:arrayType="tns:{type_}[{len(items)}]">{inner}</{name}>'


def _tags(*names):
    return _array("tags", "tag", [_i("tagId", n) + _s("tagDescr", name) for n, name in enumerate(names, 1)])


RESPONSES = {
    "getTrsType": _response("getTrsType", _array("return", "trsTypeDef", [
        _i("sType", 8) + _s("sTypeDescr", "Project 25 Phase II"),
        _i("sType", 1) + _s("sTypeDescr", "Motorola Type II Smartzone"),
    ])),
    "getTrsDetails": _response("getTrsDetails", '<return xsi:type="tns:Trs">' + _s("sName", "Example Regional P25")
                               + _i("sType", 8) + _array("sysid", "trsSysidDef", [_s("sysid", "3A1") + _s("wacn", "BEE00")])
                               + "</return>"),
    "getTrsSites": _response("getTrsSites", _array("return", "TrsSite", [
        _i("siteId", 101) + _i("siteNumber", 1) + _s("siteDescr", "North\tSimulcast") + _d("lat", "47.60")
        + _d("lon", "-122.30") + _d("range", "25") + _array("siteFreqs", "TrsSiteFreq", [
            _i("lcn", 1) + _d("freq", "851.0125") + _s("use", "d"),
            _i("lcn", 2) + _d("freq", "852.0125") + _s("use", ""),
            _i("lcn", 3) + _d("freq", "1000.0000") + _s("use", ""),  # outside the scanner: dropped
        ]),
        _i("siteId", 102) + _i("siteNumber", 2) + _s("siteDescr", "South") + _d("lat", "47.20") + _d("lon", "-122.40")
        + _d("range", "15") + _array("siteFreqs", "TrsSiteFreq", [_i("lcn", 1) + _d("freq", "853.5125") + _s("use", "d")]),
    ])),
    "getTrsTalkgroups": _response("getTrsTalkgroups", _array("return", "Talkgroup", [
        _i("tgId", 1) + _i("tgDec", 1001) + _s("tgAlpha", "FD Dispé") + _s("tgDescr", "Fire Dispatch") + _s("tgMode", "D")
        + _i("enc", 0) + _tags("Fire Dispatch") + _i("tgCid", 11) + _i("tgSort", 1),
        _i("tgId", 2) + _i("tgDec", 2001) + _s("tgAlpha", "PD Tac") + _s("tgDescr", "Police Tactical") + _s("tgMode", "DE")
        + _i("enc", 2) + _tags("Law Tac") + _i("tgCid", 12) + _i("tgSort", 2),
        _i("tgId", 3) + _i("tgDec", 2002) + _s("tgAlpha", "PD Disp") + _s("tgDescr", "Police Dispatch") + _s("tgMode", "D")
        + _i("enc", 1) + _tags("Law Dispatch") + _i("tgCid", 12) + _i("tgSort", 3),
    ])),
    "getTrsTalkgroupCats": _response("getTrsTalkgroupCats", _array("return", "TalkgroupCat", [
        _i("tgCid", 11) + _i("sid", 7971) + _s("tgCname", "Fire") + _d("lat", "47.5") + _d("lon", "-122.2") + _d("range", "30"),
        _i("tgCid", 12) + _i("sid", 7971) + _s("tgCname", "Law"),
    ])),
}

FAULT = ENVELOPE.format(body="<SOAP-ENV:Fault><faultcode>SOAP-ENV:Client</faultcode>"
                             "<faultstring>Invalid username or password</faultstring></SOAP-ENV:Fault>")

CREDS = RadioReferenceCredentials(username="operator", password="hunter2", app_key="app-key-1")


class FakeTransport:
    def __init__(self, responses=RESPONSES):
        self.responses = responses
        self.calls = []

    def __call__(self, body, action):
        self.calls.append(action)
        assert b"<appKey>app-key-1</appKey>" in body and b"<style>rpc</style>" in body
        return self.responses[action].encode("utf-8")


def _api(transport=None):
    return RadioReferenceApi(CREDS, transport=transport or FakeTransport(), spacing=0)


def _record(sid=7971):
    return _api().trunked_system(sid, _api().call("getTrsType"))


def _row(key="FLX", systems=(), text="Example Regional P25 (SID 7971)"):
    row = {name: "" for name in CSV_FIELDS}
    row.update(favorite_key=key, favorite_name="Example", system_or_category=text,
               scenario="P25 trunked dispatch", source_type="Trunked P25")
    fl = FavoritesList.from_csv_row(row)
    fl.systems = list(systems)
    return fl


def _hpdb_system(sid, tgid=9):
    channel = Channel(id=f"hpdb:tg:{sid}", label="Old TG", tgid=tgid, mode="ALL")
    site = Site(id=f"hpdb:site:{sid}", label="Old site", lat=47.6, lon=-122.3, range_miles=20, shape="Circle",
                departments=[Department(id=f"hpdb:dept:{sid}", label="Old", channels=[channel])])
    return System(id=f"hpdb:TrunkId:{sid}", label="Old", sid=sid, tech="P25Standard", sites=[site],
                  trunk_frequencies=[TrunkFrequency(id=f"hpdb:tf:{sid}", freq_mhz=851.0125, lcn=1)])


# ------------------------------------------------------------------ decoding
def test_rpc_arrays_structs_and_scalars_decode():
    record = _record()
    assert record["details"]["sName"] == "Example Regional P25" and record["details"]["sType"] == 8
    assert record["details"]["sysid"] == [{"sysid": "3A1", "wacn": "BEE00"}]
    assert [s["siteId"] for s in record["sites"]] == [101, 102]
    assert record["sites"][0]["siteFreqs"][0] == {"lcn": 1, "freq": 851.0125, "use": "d"}
    assert record["talkgroups"][0]["tags"] == [{"tagId": 1, "tagDescr": "Fire Dispatch"}]


def test_a_fault_raises_without_echoing_the_login():
    api = _api(FakeTransport({"getTrsDetails": FAULT}))
    with pytest.raises(RadioReferenceApiError) as info:
        api.call("getTrsDetails", sid=7971)
    assert "Invalid username or password" in str(info.value)
    assert "hunter2" not in str(info.value) and "app-key-1" not in str(info.value)


# --------------------------------------------------------------- credentials
def test_login_comes_from_the_environment_then_windows_credential_manager():
    from_env = resolve_credentials("k", environ={USERNAME_ENV: "u", PASSWORD_ENV: "p"}, credential_reader=None)
    assert from_env.is_configured() and (from_env.username, from_env.password) == ("u", "p")
    stored = resolve_credentials("k", environ={}, credential_reader=lambda target: ("stored-user", "stored-pw"))
    assert (stored.username, stored.password, stored.app_key) == ("stored-user", "stored-pw", "k")
    assert not resolve_credentials("k", environ={}, credential_reader=lambda target: None).is_configured()
    assert "stored-pw" not in repr(stored)


def test_fetch_without_a_login_says_how_to_store_one():
    with pytest.raises(RadioReferenceApiError, match="cmdkey /generic:wasds150-radioreference"):
        RadioReferenceApiSource(RadioReferenceCredentials(app_key="k"), sids=(7971,)).fetch()


# ------------------------------------------------------------ system builder
def test_a_p25_system_is_built_whole_and_validates_for_the_scanner():
    system, notes = system_from_api(_record())
    assert notes == []
    assert (system.id, system.sid, system.tech, system.wacn) == ("rrapi:TrunkId:7971", 7971, "P25Standard", "BEE00")
    assert [s.label for s in system.sites] == ["001 North Simulcast", "002 South"]
    assert system.sites[0].shape == "Circle" and system.sites[0].range_miles == 25
    assert sorted(tf.freq_mhz for tf in system.trunk_frequencies) == [851.0125, 852.0125, 853.5125]
    departments = {d.label: d for d in system.sites[-1].departments}
    assert set(departments) == {"Fire", "Law"}
    assert departments["Fire"].range_miles == 30 and departments["Law"].lat is None
    from wasds150.recipes.rr_county import _service_type as service_type_for_tag

    fire = departments["Fire"].channels[0]
    assert (fire.label, fire.tgid, fire.mode, fire.avoid) == ("FD Disp?", 1001, "ALL", False)
    # RadioReference tags map to the scanner's service types through the same
    # table the county lists use.
    assert fire.service_type == service_type_for_tag("Fire Dispatch") is not None
    law = {c.tgid: c for c in departments["Law"].channels}
    assert law[2001].avoid is True and "encrypted" in law[2001].notes
    assert law[2002].avoid is False and "partly encrypted" in law[2002].notes

    fl = _row(systems=[system])
    assert validate_favorites_list(fl) == []


def test_a_non_p25_system_is_skipped_with_the_reason():
    record = _record()
    record["details"] = dict(record["details"], sType=1)
    system, notes = system_from_api(record)
    assert system is None and "Motorola Type II Smartzone is not Project 25" in notes[0]


# ------------------------------------------------------------------- adapter
def test_adapter_fetches_each_named_system_and_normalizes_to_licensed_facts():
    transport = FakeTransport()
    source = RadioReferenceApiSource(CREDS, sids=(7971,), api=RadioReferenceApi(CREDS, transport=transport, spacing=0))
    raw = source.fetch()
    assert transport.calls == ["getTrsType", "getTrsDetails", "getTrsSites", "getTrsTalkgroups", "getTrsTalkgroupCats"]
    result = source.normalize(raw)
    (fact,) = result.facts
    assert fact.entity_key == "radioreference_api:TrunkId:7971" and fact.fact_type == "system"
    assert (fact.raw["sid"], fact.raw["talkgroups"], fact.raw["sites"]) == (7971, 3, 2)


def test_the_catalog_names_the_systems_to_fetch():
    sids = catalog_system_ids()
    assert {7971, 11628, 10705} <= set(sids)


def test_factory_builds_the_source_only_once_an_app_key_is_configured():
    assert instantiate_source("radioreference_api", SourcesConfig()) is None
    assert isinstance(instantiate_source("radioreference_api", SourcesConfig(radioreference_app_key="k")), RadioReferenceApiSource)


# -------------------------------------------------------------------- engine
def _facts():
    source = RadioReferenceApiSource(CREDS, sids=(7971,), api=_api())
    return source.normalize(source.fetch()).facts


def test_a_live_system_replaces_the_older_copy_of_its_sid_and_keeps_the_rest():
    fl = _row(systems=[_hpdb_system(7971), _hpdb_system(1234)])
    catalog = Catalog(favorites=[fl])
    enriched = enrich_catalog(catalog, _facts(), build_default_recipes(catalog)).catalog
    ids = [s.id for s in enriched.favorites[0].systems]
    assert "rrapi:TrunkId:7971" in ids and "hpdb:TrunkId:1234" in ids
    assert "hpdb:TrunkId:7971" not in ids


def test_a_refresh_replaces_the_previous_live_copy():
    fl = _row()
    catalog = Catalog(favorites=[fl])
    first = enrich_catalog(catalog, _facts(), build_default_recipes(catalog)).catalog
    second = enrich_catalog(first, _facts(), build_default_recipes(first)).catalog
    assert [s.id for s in second.favorites[0].systems].count("rrapi:TrunkId:7971") == 1


def test_an_export_frequency_list_never_overwrites_a_live_site_table():
    system, _ = system_from_api(_record())
    fl = _row(systems=[system])
    site_fact = NormalizedFact(entity_key="rr:site", fact_type="site", name="Site 1", freq_mhz=860.0,
                               source_id="radioreference_premium", raw={"sid": 7971, "rr_category": "Example"})
    refreshed, _message = refresh_trunk_frequencies(fl, [site_fact], sids=(7971,))
    assert refreshed is False
    assert 860.0 not in [tf.freq_mhz for tf in fl.systems[0].trunk_frequencies]
