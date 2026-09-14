"""DSTARInfo: the directory's pages parse, the form postback is cached, and
no record reaches a list. Invented calls; no test touches the network."""
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import urllib.parse

import pytest

from wasds150.cache.http import CachedHttpClient, RateLimiter
from wasds150.cache.store import HttpCacheStore
from wasds150.sources.base import RawDoc
from wasds150.sources.dstarinfo import AREAS, DStarInfoSource, parse_module


def _row(index, call, city, state, c="", b="", a="", dd="", info="", register=""):
    links = "".join(
        f'<a href="{url}" target="_blank">{kind}</a>' for url, kind in ((info, "Info"), (register, "Register")) if url
    )
    return f"""<tr><td><a href="http://apps.dstarinfo.com/Repeater.aspx?Repeater={call}" target="_blank">
    {call}</a>{links}</td>
    <td><span id="ListView1_CityLabel_{index}">{city}</span></td>
    <td><span id="ListView1_CountryStateLabel_{index}">{state}</span></td>
    <td><span id="ListView1_ircDDBTextLabel_{index}">ircDDB</span><span id="ListView1_USROOTTextLabel_{index}"></span></td>
    <td><span id="ListView1_C_ModLabel_{index}">{c}</span></td>
    <td><span id="ListView1_B_ModLabel_{index}">{b}</span></td>
    <td><span id="ListView1_A_ModLabel_{index}">{a}</span></td>
    <td><span id="ListView1_DD_ModLabel_{index}">{dd}</span></td></tr>"""


LIST = "<table><tr><th>Callsign</th></tr>" + "".join((
    _row(1, "W7TST", "Bellevue", "United States, Washington", c="146.4125 +1.0000", b="443.0625 +5.0000",
         a="1290.0000 -20.0000", dd="1247.0000 RPS", info="http://club.example", register="https://gw.example"),
    _row(2, "K7XMP", "Salem", "United States, Oregon", c="147.0400 0.6"),
    _row(3, "K7XMP", "Salem", "United States, Oregon", c="147.0400 0.6"),  # listed twice
    _row(4, "N6DST", "Phoenix", "United States, Arizona", b="444.1000 +5.0000"),
)) + "</table>"
DETAIL = """<span id="DataList1_CallsignLabel_0">W7TST</span>
<span id="DataList1_SponsorLabel_0">Test Radio Club</span>
<span id="DataList1_Coverage_DescriptionLabel_0">Puget Sound</span>
<span id="DataList1_Information_EmailLabel_0">owner@example.test</span>"""


def test_the_directory_gives_one_fact_per_module():
    raw = RawDoc("dstarinfo", {"areas": {"USA West": LIST}, "details": {"W7TST": DETAIL}, "errors": []}, "2026-09-13")
    facts = {f.entity_key: f for f in DStarInfoSource().normalize(raw).facts}
    assert sorted(facts) == [
        "dstarinfo:K7XMP:C", "dstarinfo:N6DST:B",
        "dstarinfo:W7TST:A", "dstarinfo:W7TST:B", "dstarinfo:W7TST:C", "dstarinfo:W7TST:DD",
    ]
    c = facts["dstarinfo:W7TST:C"]
    assert (c.freq_mhz, c.offset_mhz, c.tx_freq_mhz, c.mode) == (146.4125, 1.0, 147.4125, "DV")
    assert (c.raw["rpt1"], c.raw["rpt2"]) == ("W7TST  C", "W7TST  G")
    assert c.raw["register_url"] == "https://gw.example" and c.raw["details"]["Sponsor"] == "Test Radio Club"
    assert "Information_Email" not in c.raw["details"]  # the owner's address is not kept
    assert (facts["dstarinfo:W7TST:DD"].mode, facts["dstarinfo:W7TST:DD"].offset_mhz) == ("DD", None)
    # An offset without a sign has no direction: never guessed.
    assert facts["dstarinfo:K7XMP:C"].tx_freq_mhz is None


def test_module_cells():
    assert parse_module("443.0625 +5.0000") == (443.0625, 5.0, "")
    assert parse_module("434.0000 +0.0000") == (434.0, 0.0, "")
    assert parse_module("145.6750 - 0.6000") == (145.675, -0.6, "")
    assert parse_module("1247.0000 RPS")[1] is None
    assert parse_module("not a frequency") is None


class _Http:
    def __init__(self):
        self.forms, self.pages = [], []

    def fetch_form(self, url, *, fields, cache_key, ttl_seconds, source_id, event_target=""):
        self.forms.append((fields["Countries1"], event_target, cache_key))
        return type("R", (), {"content": (LIST if fields["Countries1"] == "USA West" else "<p>No data was returned.</p>").encode()})

    def fetch(self, url, *, ttl_seconds, source_id):
        self.pages.append(url)
        return type("R", (), {"content": DETAIL.encode()})


def test_every_area_is_fetched_and_details_only_near_home():
    http = _Http()
    raw = DStarInfoSource().fetch(http)
    assert [area for area, _target, _key in http.forms] == list(AREAS)
    assert all(target == "Countries1" and key.endswith(f"#Countries1={area}") for area, target, key in http.forms)
    assert sorted(url.rsplit("=", 1)[1] for url in http.pages) == ["K7XMP", "W7TST"]  # not Arizona
    assert set(raw.payload["details"]) == {"K7XMP", "W7TST"}


def test_a_dstarinfo_record_reaches_no_list():
    from wasds150.models.catalog import CSV_FIELDS, FavoritesList
    from wasds150.recipes.systems import systems_from_flat_facts

    row = {field: "" for field in CSV_FIELDS}
    row.update(favorite_key="PSHAM02", favorite_name="Ham list")
    raw = RawDoc("dstarinfo", {"areas": {"USA West": LIST}, "details": {}}, "2026-09-13")
    assert systems_from_flat_facts(FavoritesList.from_csv_row(row), DStarInfoSource().normalize(raw).facts) == []


@pytest.fixture
def form_server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            self.server.requests.append("GET")
            body = b'<form><input type="hidden" name="__VIEWSTATE" id="__VIEWSTATE" value="a&amp;b" /></form>'
            self.send_response(200)
            self.send_header("Set-Cookie", "session=1")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            self.server.requests.append("POST")
            length = int(self.headers["Content-Length"])
            posted = urllib.parse.parse_qs(self.rfile.read(length).decode())
            self.server.posted = (posted, self.headers.get("Cookie"))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"answer for " + posted["Countries1"][0].encode())

    server = HTTPServer(("127.0.0.1", 0), Handler)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def test_a_form_postback_sends_the_page_state_and_caches_the_answer(tmp_path, form_server):
    client = CachedHttpClient(HttpCacheStore(tmp_path / "cache"), rate_limiter=RateLimiter(min_interval_seconds=0))
    url = f"http://127.0.0.1:{form_server.server_port}/list.aspx"
    kwargs = dict(fields={"Countries1": "USA West"}, event_target="Countries1", cache_key=url + "#USA West",
                  ttl_seconds=3600, source_id="dstarinfo")
    first = client.fetch_form(url, **kwargs)
    posted, cookie = form_server.posted
    assert first.status == "fetched" and first.content == b"answer for USA West"
    assert posted["__VIEWSTATE"] == ["a&b"] and posted["__EVENTTARGET"] == ["Countries1"] and cookie == "session=1"
    assert client.fetch_form(url, **kwargs).status == "cached-fresh"
    assert form_server.requests == ["GET", "POST"]
