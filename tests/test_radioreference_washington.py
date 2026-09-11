"""The full Washington pull from the RadioReference web service: persisted
snapshot, incremental reruns, the change report, and the lists it builds.

A small fake Washington answers in the service's RPC/encoded shape, with
made-up values: no licensed data, no network.
"""
from __future__ import annotations

import copy
import datetime
import json
import re
from xml.sax.saxutils import escape

import pytest

from wasds150.models.catalog import Catalog
from wasds150.recipes.engine import enrich_catalog
from wasds150.recipes.rr_county import build_rr_favorites, build_rr_trunked_favorites
from wasds150.sources.facts import NormalizedFact
from wasds150.sources.radioreference_api import RadioReferenceApi, RadioReferenceApiSource
from wasds150.sources.radioreference_premium import RadioReferenceCredentials

CREDS = RadioReferenceCredentials(username="operator", password="hunter2", app_key="app-key-1")
T0 = datetime.datetime(2026, 9, 11, 12, 0, tzinfo=datetime.timezone.utc)

ENVELOPE = (
    '<?xml version="1.0" encoding="utf-8"?><SOAP-ENV:Envelope '
    'xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" '
    'xmlns:tns="http://api.radioreference.com/soap2"><SOAP-ENV:Body>'
    '<ns1:{op}Response xmlns:ns1="http://api.radioreference.com/soap2">{value}</ns1:{op}Response>'
    "</SOAP-ENV:Body></SOAP-ENV:Envelope>"
)
FAULT = ENVELOPE.replace("<ns1:{op}Response xmlns:ns1=\"http://api.radioreference.com/soap2\">{value}</ns1:{op}Response>",
                         "<SOAP-ENV:Fault><faultstring>{value}</faultstring></SOAP-ENV:Fault>")


def xml(name, value):
    if isinstance(value, bool):
        return f'<{name} xsi:type="xsd:boolean">{int(value)}</{name}>'
    if isinstance(value, int):
        return f'<{name} xsi:type="xsd:int">{value}</{name}>'
    if isinstance(value, float):
        return f'<{name} xsi:type="xsd:decimal">{value}</{name}>'
    if isinstance(value, list):
        items = "".join(xml("item", v) for v in value)
        return f'<{name} xsi:type="SOAP-ENC:Array" SOAP-ENC:arrayType="tns:x[{len(value)}]">{items}</{name}>'
    if isinstance(value, dict):
        return f'<{name} xsi:type="tns:Struct">' + "".join(xml(k, v) for k, v in value.items()) + f"</{name}>"
    return f'<{name} xsi:type="xsd:string">{escape(str(value))}</{name}>'


def _system(sid, name, stype, counties, tgs):
    return {
        "details": {"sName": name, "sType": stype, "sCounty": [{"ctid": c} for c in counties],
                    "sysid": [{"sysid": "3A1", "wacn": "BEE00"}]},
        "sites": [{"siteId": sid * 10, "siteNumber": 1, "siteDescr": "Main", "lat": 47.6, "lon": -122.3, "range": 20.0,
                   "siteFreqs": [{"lcn": 1, "freq": 851.0125, "use": "d"}]}],
        "talkgroups": [{"tgDec": dec, "tgAlpha": alpha, "tgDescr": alpha, "tgMode": "D", "enc": 0, "tgCid": 1,
                        "tgSort": i, "tags": [{"tagId": 3}]} for i, (dec, alpha) in enumerate(tgs)],
        "categories": [{"tgCid": 1, "tgCname": "Fire"}],
    }


def washington():
    return {
        "types": [{"sType": 8, "sTypeDescr": "Project 25 Phase II"}, {"sType": 1, "sTypeDescr": "Motorola Type II Smartnet"}],
        "modes": [{"mode": 2, "modeName": "FMN"}, {"mode": 4, "modeName": "P25"}],
        "tags": [{"tagId": 3, "tagDescr": "Fire Dispatch"}, {"tagId": 8, "tagDescr": "Law Dispatch"}],
        "state": {"stid": 53, "stateName": "Washington",
                  "countyList": [{"ctid": 2974, "countyName": "King"}, {"ctid": 2988, "countyName": "Snohomish"}],
                  "agencyList": [{"aid": 555, "aName": "Washington State Patrol", "aType": 1}],
                  "trsList": [{"sid": 7971, "sName": "WA State Patrol", "lastUpdated": "L1"},
                              {"sid": 9001, "sName": "Example County P25", "lastUpdated": "L1"},
                              {"sid": 9002, "sName": "Legacy Smartnet", "lastUpdated": "L1"}]},
        "counties": {
            2974: {"ctid": 2974, "countyName": "King", "lastUpdated": "2026-09-01T00:00:00",
                   "cats": [{"cid": 1, "cName": "King County Fire", "subcats": [{"scid": 101, "scName": "Dispatch"}]}],
                   "trsList": [{"sid": 9001, "sName": "Example County P25", "lastUpdated": "L1"}],
                   "agencyList": [{"aid": 777, "aName": "Businesses", "aType": 2}]},
            2988: {"ctid": 2988, "countyName": "Snohomish", "lastUpdated": "2026-09-01T00:00:00",
                   "cats": [{"cid": 2, "cName": "Snohomish Sheriff", "subcats": [{"scid": 201, "scName": "Law"}]}],
                   "trsList": []},
        },
        "agencies": {555: {"aid": 555, "agencyName": "Washington State Patrol", "lastUpdated": "2026-08-01T00:00:00",
                           "cats": [{"cid": 3, "cName": "WSP", "subcats": [{"scid": 301, "scName": "District 1"}]}]},
                     # An agency King County lists itself: its rows belong to King's list.
                     777: {"aid": 777, "agencyName": "Businesses", "lastUpdated": "2026-08-01T00:00:00",
                           "cats": [{"cid": 7, "cName": "Businesses", "subcats": [{"scid": 701, "scName": "Utilities"}]}]}},
        "freqs": {
            101: [{"fid": 1, "out": 154.43, "in": 0.0, "tone": "CSQ", "mode": "2", "descr": "Fire Dispatch",
                   "alpha": "KCFD Disp", "callsign": "KAB1", "enc": 0, "tags": [{"tagId": 3}]}],
            201: [{"fid": 2, "out": 155.97, "in": 156.12, "tone": "103.5 PL", "mode": "2", "descr": "Sheriff Dispatch",
                   "alpha": "SCSO Disp", "callsign": "", "enc": 0, "tags": [{"tagId": 8}]}],
            301: [{"fid": 3, "out": 460.2, "in": 465.2, "tone": "293 NAC", "mode": "4", "descr": "District 1",
                   "alpha": "WSP D1", "callsign": "", "enc": 0, "tags": [{"tagId": 8}]}],
            701: [{"fid": 7, "out": 451.5, "in": 456.5, "tone": "100.0 PL", "mode": "2", "descr": "Water Utility",
                   "alpha": "Water", "callsign": "", "enc": 0, "tags": []}],
        },
        "systems": {
            7971: _system(7971, "WA State Patrol", 8, [2974, 2988], [(100, "WSP Car 1")]),
            9001: _system(9001, "Example County P25", 8, [2974], [(200, "FD Disp")]),
            9002: _system(9002, "Legacy Smartnet", 1, [2988], [(300, "Old TG")]),
        },
    }


class FakeService:
    def __init__(self, data):
        self.data = data
        self.calls = []
        self.fail = {}

    def __call__(self, body, action):
        text = body.decode("utf-8")
        inner = re.search(rf"<rr:{action}>(.*?)<authInfo>", text, re.S).group(1)
        params = {k: int(v) for k, v in re.findall(r"<(\w+)>(\d+)</\1>", inner)}
        self.calls.append((action, params))
        if (action, tuple(sorted(params.items()))) in self.fail:
            raise self.fail[(action, tuple(sorted(params.items())))]
        d = self.data
        value = {
            "getTrsType": lambda: d["types"],
            "getMode": lambda: d["modes"],
            "getTag": lambda: d["tags"],
            "getStateInfo": lambda: d["state"],
            "getCountyInfo": lambda: d["counties"][params["ctid"]],
            "getAgencyInfo": lambda: d["agencies"][params["aid"]],
            "getSubcatFreqs": lambda: d["freqs"].get(params["scid"], []),
            "getTrsDetails": lambda: d["systems"][params["sid"]]["details"],
            "getTrsSites": lambda: d["systems"][params["sid"]]["sites"],
            "getTrsTalkgroups": lambda: d["systems"][params["sid"]]["talkgroups"],
            "getTrsTalkgroupCats": lambda: d["systems"][params["sid"]]["categories"],
        }[action]()
        return ENVELOPE.format(op=action, value=xml("return", value)).encode("utf-8")

    def called(self, action, **params):
        return [c for c in self.calls if c[0] == action and all(c[1].get(k) == v for k, v in params.items())]


def _source(service, store, now=T0, **kwargs):
    return RadioReferenceApiSource(
        CREDS, api=RadioReferenceApi(CREDS, transport=service, spacing=0), store_dir=store, now=now,
        extra_sids=(7971,), **kwargs,
    )


def _run(service, store, now=T0, **kwargs):
    source = _source(service, store, now, **kwargs)
    raw = source.fetch()
    return raw, source.normalize(raw)


# ------------------------------------------------------------- the full pull
def test_first_pull_persists_the_state_and_turns_it_into_facts(tmp_path):
    raw, result = _run(FakeService(washington()), tmp_path)
    assert (tmp_path / "snapshot.json").is_file()
    assert raw.payload["full"] is True
    assert result.warnings[0].startswith("RadioReference Washington baseline: 4 frequencies")
    assert any("Legacy Smartnet" in w and "not Project 25" in w for w in result.warnings)

    freqs = {f.raw["fid"]: f for f in result.facts if f.fact_type == "frequency"}
    assert {f.county for f in freqs.values()} == {"King", "Snohomish", "Statewide"}
    # an agency the county lists itself (its businesses) lands in that county's list
    assert (freqs[7].county, freqs[7].raw["rr_category"]) == ("King", "Businesses Utilities")
    assert (freqs[1].mode, freqs[1].raw["rr_tag"], freqs[1].raw["rr_category"]) == ("NFM", "Fire Dispatch", "King County Fire Dispatch")
    assert (freqs[2].tone, freqs[2].tx_freq_mhz) == ("TONE=C103.5", 156.12)
    assert (freqs[3].mode, freqs[3].tone) == ("P25", "NAC=293")

    systems = {f.raw["sid"]: f for f in result.facts if f.fact_type == "system"}
    assert set(systems) == {7971, 9001}
    assert systems[9001].county == "King" and systems[7971].county == "Statewide"

    report = sorted((tmp_path / "runs").glob("*.md"))
    assert report and "First complete pull" in report[-1].read_text(encoding="utf-8")


def test_web_service_rows_replace_the_export_in_the_county_lists(tmp_path):
    _raw, result = _run(FakeService(washington()), tmp_path)
    export_row = NormalizedFact(entity_key="rr:x", fact_type="frequency", name="Old export row", freq_mhz=154.43,
                                mode="FM", county="King", source_id="radioreference_premium", raw={"rr_category": "Old"})
    lists = {fl.favorite_key: fl for fl in build_rr_favorites(result.facts + [export_row])}
    king = [c.label for s in lists["RRC-KING"].systems for d in s.departments for c in d.channels]
    assert king == ["Fire Dispatch", "Water Utility"]  # the export row is gone; the county's agency row is in
    assert {"RRC-KING", "RRC-SNOHOMISH", "RRWA"} <= set(lists)


def test_systems_no_catalog_row_names_get_their_own_county_lists(tmp_path):
    _raw, result = _run(FakeService(washington()), tmp_path)
    lists = {fl.favorite_key: fl for fl in build_rr_trunked_favorites(result.facts, exclude_sids={7971})}
    assert list(lists) == ["RRT-KING"]
    assert [s.sid for s in lists["RRT-KING"].systems] == [9001] and lists["RRT-KING"].licensed

    enriched = enrich_catalog(Catalog(favorites=[]), result.facts, []).catalog
    keys = {fl.favorite_key for fl in enriched.favorites}
    assert {"RRC-KING", "RRT-KING", "RRT-WA"} <= keys


# ------------------------------------------------------- reruns and changes
def _changed(data):
    data = copy.deepcopy(data)
    data["counties"][2974]["lastUpdated"] = "2026-09-10T00:00:00"
    data["freqs"][101][0]["tone"] = "107.2 PL"
    data["freqs"][101].append({"fid": 4, "out": 154.25, "in": 0.0, "tone": "CSQ", "mode": "2", "descr": "Fire Tac",
                               "alpha": "KCFD Tac", "callsign": "", "enc": 0, "tags": [{"tagId": 3}]})
    data["counties"][2988]["lastUpdated"] = "2026-09-10T00:00:00"
    data["freqs"][201] = []
    data["state"]["trsList"][1]["lastUpdated"] = "L2"
    data["systems"][9001]["talkgroups"].append({"tgDec": 201, "tgAlpha": "FD Tac", "tgDescr": "Fire Tac", "tgMode": "D",
                                                "enc": 0, "tgCid": 1, "tgSort": 9, "tags": []})
    return data


def test_a_rerun_fetches_only_what_moved_and_reports_the_changes(tmp_path):
    _run(FakeService(washington()), tmp_path)
    service = FakeService(_changed(washington()))
    raw, result = _run(service, tmp_path, now=T0 + datetime.timedelta(days=1))

    assert raw.payload["full"] is False
    assert service.called("getSubcatFreqs", scid=101) and service.called("getSubcatFreqs", scid=201)
    assert not service.called("getSubcatFreqs", scid=301)  # the agency did not move
    assert service.called("getTrsTalkgroups", sid=9001) and not service.called("getTrsTalkgroups", sid=7971)

    summary = result.warnings[0]
    assert "frequencies +1 -1 ~1" in summary and "talkgroups +1 -0 ~0" in summary
    report = json.loads(sorted((tmp_path / "runs").glob("*.json"))[-1].read_text(encoding="utf-8"))
    assert [c["changes"] for c in report["frequencies"]["changed"]] == [{"tone": ["CSQ", "107.2 PL"]}]
    assert [a["key"] for a in report["frequencies"]["added"]] == ["4"]
    assert [r["key"] for r in report["frequencies"]["removed"]] == ["2"]
    markdown = sorted((tmp_path / "runs").glob("*.md"))[-1].read_text(encoding="utf-8")
    assert "## Frequencies added (1)" in markdown and "tone 'CSQ' -> '107.2 PL'" in markdown

    unchanged = {f.raw["fid"] for f in result.facts if f.fact_type == "frequency"}
    assert unchanged == {1, 3, 4, 7}  # the agencies' rows were reused, not lost


def test_everything_is_refetched_once_the_full_refresh_is_due(tmp_path):
    _run(FakeService(washington()), tmp_path)
    service = FakeService(washington())
    raw, _result = _run(service, tmp_path, now=T0 + datetime.timedelta(days=8))
    assert raw.payload["full"] is True
    assert service.called("getSubcatFreqs", scid=301) and service.called("getTrsTalkgroups", sid=7971)


def test_a_failed_subcategory_keeps_its_last_known_rows(tmp_path):
    from wasds150.sources.radioreference_api import RadioReferenceApiError

    _run(FakeService(washington()), tmp_path)
    data = washington()
    data["counties"][2974]["lastUpdated"] = "2026-09-10T00:00:00"
    service = FakeService(data)
    service.fail[("getSubcatFreqs", (("scid", 101),))] = RadioReferenceApiError("getSubcatFreqs: busy")
    _raw, result = _run(service, tmp_path, now=T0 + datetime.timedelta(days=1))
    assert 1 in {f.raw["fid"] for f in result.facts if f.fact_type == "frequency"}
    assert any("subcategory 101" in w for w in result.warnings)
    assert "frequencies +0 -0 ~0" in result.warnings[0]


def test_an_interrupted_pull_resumes_instead_of_starting_again(tmp_path):
    service = FakeService(washington())
    service.fail[("getSubcatFreqs", (("scid", 201),))] = RuntimeError("connection dropped")
    with pytest.raises(RuntimeError):
        _source(service, tmp_path, checkpoint_every=1).fetch()
    assert (tmp_path / "snapshot.partial.json").is_file() and not (tmp_path / "snapshot.json").exists()

    resumed = FakeService(washington())
    raw = _source(resumed, tmp_path, now=T0 + datetime.timedelta(hours=1), checkpoint_every=1).fetch()
    assert not resumed.called("getSubcatFreqs", scid=101)  # fetched before the drop
    assert resumed.called("getSubcatFreqs", scid=201)
    assert raw.payload["snapshot"]["complete"] and not (tmp_path / "snapshot.partial.json").exists()


class BrokenTypeLookup(FakeService):
    """RadioReference's getTrsType answers with an empty body (seen live on
    2026-09-11, as do getTrsFlavor and getTrsVoice)."""

    def __call__(self, body, action):
        if action == "getTrsType":
            self.calls.append((action, {}))
            return b""
        return super().__call__(body, action)


def test_the_pull_survives_the_broken_type_lookup(tmp_path):
    _raw, result = _run(BrokenTypeLookup(washington()), tmp_path)
    systems = {f.raw["sid"] for f in result.facts if f.fact_type == "system"}
    assert systems == {7971, 9001}  # type 8 is still known to be Project 25
    assert any("Legacy Smartnet" in w and "type 1 is not Project 25" in w for w in result.warnings)
