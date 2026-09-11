"""RepeaterBook adapter: the acceptance criteria in
``docs/repeaterbook-api-compliance-design.md`` and the multi-region policy.

Synthetic fixtures only -- no record here was ever returned by RepeaterBook.
No test touches the network: every request goes through a fake transport, and
the real one is replaced by a function that fails the test if it is called.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

import pytest

from wasds150.config import AppConfig
from wasds150.sources.config import SourcesConfig
from wasds150.sources.repeaterbook import policy
from wasds150.sources.repeaterbook import client as client_mod
from wasds150.sources.repeaterbook.catalog import detail_url
from wasds150.sources.repeaterbook.client import (
    AuthError,
    BadRequest,
    HttpResponse,
    RateLimited,
    RepeaterBookClient,
    ResponseError,
    TransientError,
    UserAgentRefused,
    build_export_url,
    classify,
    parse_retry_after,
)
from wasds150.sources.repeaterbook.normalize import great_circle_miles
from wasds150.sources.repeaterbook.service import (
    CandidateCapError,
    LimitError,
    NotEnabledError,
    PolicyError,
    RefreshRequest,
    RepeaterBookService,
    TokenMissingError,
    format_preview,
    purge_on_startup,
    validate_request,
)
from wasds150.sources.repeaterbook.store import ActionInProgress, RepeaterBookStore
from wasds150.sources.repeaterbook.token import Token, TokenError, load_token, validate_token

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKEN = "rbuapp_" + "SyntheticT0ken" * 3
T0 = datetime.datetime(2026, 9, 10, 12, 0, tzinfo=datetime.timezone.utc)
CENTER = (47.633, -121.966)
ATTRIBUTION_MD = "[Data courtesy of RepeaterBook.com](https://www.repeaterbook.com/)"


class Clock:
    def __init__(self, now: datetime.datetime = T0):
        self.now = now

    def __call__(self) -> datetime.datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += datetime.timedelta(**kwargs)


def record(i: int, *, state_id: str = "53", lat=None, lon=None, freq: float = 146.0, input_freq="default",
           pl: str = "100.0", tsq: str = "", analog: str = "Yes", status: str = "On-air", use: str = "OPEN",
           **extra) -> dict:
    """A synthetic record in the shape this adapter expects (see normalize.FIELDS)."""
    rec = {
        "State ID": state_id,
        "Rptr ID": str(1000 + i),
        "Frequency": f"{freq:.5f}",
        "Input Freq": f"{freq - 0.6:.5f}" if input_freq == "default" else input_freq,
        "PL": pl,
        "TSQ": tsq,
        "Nearest City": f"Town{i}",
        "County": "Synthetic",
        "State": "Washington",
        "Country": "United States",
        "Lat": str(CENTER[0] + 0.001 * (i % 100) if lat is None else lat),
        "Long": str(CENTER[1] if lon is None else lon),
        "Callsign": f"W7T{i:03d}",
        "Use": use,
        "Operational Status": status,
        "FM Analog": analog,
        "Last Update": "2026-01-01",
    }
    rec.update(extra)
    return rec


def body(records) -> bytes:
    return json.dumps({"count": len(records), "results": list(records)}).encode("utf-8")


def ok(records=None) -> HttpResponse:
    return HttpResponse(200, {}, body(records if records is not None else [record(1)]))


class FakeTransport:
    """Records every request; answers from a queue, then with one record."""

    def __init__(self, responses=()):
        self.calls = []
        self.responses = list(responses)
        self.in_flight = 0
        self.max_in_flight = 0

    def __call__(self, url, headers, timeout, max_bytes):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            self.calls.append({"url": url, "headers": dict(headers)})
            return self.responses.pop(0) if self.responses else ok()
        finally:
            self.in_flight -= 1


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("a test tried to reach RepeaterBook")

    monkeypatch.setattr(client_mod, "urllib_transport", refuse)


@pytest.fixture()
def home(tmp_path, monkeypatch) -> AppConfig:
    monkeypatch.setenv("WASDS150_HOME", str(tmp_path / "home"))
    monkeypatch.delenv(policy.DEFAULT_TOKEN_ENV, raising=False)
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return config


def enable(config: AppConfig, enabled: bool = True) -> None:
    cfg = SourcesConfig.load(config.sources_config_path)
    cfg.repeaterbook_enabled = enabled
    cfg.save(config.sources_config_path)


def service(config, transport=None, clock=None, token=TOKEN) -> RepeaterBookService:
    environ = {policy.DEFAULT_TOKEN_ENV: token} if token else {}
    return RepeaterBookService(config, clock=clock or Clock(), transport=transport or FakeTransport(), environ=environ)


def request(regions=("WA",), radius=60, bands=("2m", "70cm"), radio="th-d75") -> RefreshRequest:
    return RefreshRequest(regions=tuple(regions), center=CENTER, radius_mi=radius, bands=tuple(bands), radio_id=radio)


# -- 1. the exact User-Agent ---------------------------------------------------------
def test_user_agent_is_the_approved_string_with_project_url_and_contact():
    assert policy.USER_AGENT == (
        "SignalWA/1.0 (+https://github.com/NiyaNagi/washington-sds150-favorites; ajamess@gmail.com)"
    )


def test_request_sends_the_exact_user_agent_and_the_token_only_in_its_header(home):
    enable(home)
    transport = FakeTransport()
    service(home, transport).refresh(request())
    (call,) = transport.calls
    assert call["headers"]["User-Agent"] == policy.USER_AGENT
    assert call["headers"]["X-RB-App-Token"] == TOKEN
    assert TOKEN not in call["url"]


def test_the_shared_default_user_agent_is_refused_before_sending():
    from wasds150.cache.http import DEFAULT_USER_AGENT

    transport = FakeTransport()
    for agent in (DEFAULT_USER_AGENT, "Python-urllib/3.12", ""):
        client = RepeaterBookClient(Token(TOKEN, "test"), transport=transport, user_agent=agent)
        with pytest.raises(UserAgentRefused):
            client.export(policy.REGIONS["WA"], now=T0)
    assert transport.calls == []


# -- 2. token rules ------------------------------------------------------------------------
@pytest.mark.parametrize("value", ["", "   ", "abc", "app_" + "x" * 24, "rbuapp_", "rbuapp_has space", "RBUAPP_x"])
def test_token_prefix_rules(value):
    with pytest.raises(TokenError):
        validate_token(value)


def test_shared_app_token_is_rejected_without_quoting_it():
    shared = "app_" + "SharedSecret" * 3
    with pytest.raises(TokenError) as exc:
        validate_token(shared)
    assert "rbuapp_" in str(exc.value)
    assert shared not in str(exc.value)


def test_rbuapp_token_is_accepted_and_never_shown():
    token = Token(f"  {TOKEN}\n", source="test")
    assert token.reveal() == TOKEN
    assert TOKEN not in repr(token) and TOKEN not in str(token)
    assert len(token.fingerprint) == 16


def test_token_from_an_external_file(tmp_path):
    path = tmp_path / "outside" / "rb-token.txt"
    path.parent.mkdir()
    path.write_text(TOKEN + "\n", encoding="utf-8")
    token = load_token(token_file=str(path), environ={}, repo_root=tmp_path / "repo")
    assert token.reveal() == TOKEN and token.source == "file"


def test_token_file_inside_the_repository_or_relative_is_refused(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    inside = repo / "token.txt"
    inside.write_text(TOKEN, encoding="utf-8")
    with pytest.raises(TokenError):
        load_token(token_file=str(inside), environ={}, repo_root=repo)
    with pytest.raises(TokenError):
        load_token(token_file="token.txt", environ={}, repo_root=repo)


def test_configuration_stores_only_where_the_token_is(home, tmp_path):
    path = tmp_path / "outside" / "rb-token.txt"
    path.parent.mkdir()
    path.write_text(TOKEN, encoding="utf-8")
    svc = service(home)
    svc.configure(enabled=True, token_env="MY_RB_TOKEN")
    svc.configure(token_file=str(path))
    text = home.sources_config_path.read_text(encoding="utf-8")
    assert TOKEN not in text
    assert "MY_RB_TOKEN" in text and "rb-token.txt" in text
    with pytest.raises(TokenError):
        svc.configure(token_env=TOKEN)  # a token pasted where a name belongs


# -- 3. redaction -------------------------------------------------------------------------------
def test_token_never_reaches_the_store_logs_reports_or_config(home):
    from wasds150.logging_setup import configure_logging

    configure_logging(home.log_file)
    enable(home)
    echoed = ok([record(1, Notes=f"server echoed {TOKEN}")])
    svc = service(home, FakeTransport([echoed]))
    svc.refresh(request())
    svc.write_review_report("md")
    svc.write_review_report("html")
    svc.apply()
    logging.getLogger("wasds150.sources.repeaterbook").error("child logger token=%s %s", TOKEN, TOKEN)
    logging.getLogger("wasds150").warning("plain %s", TOKEN)
    for handler in logging.getLogger("wasds150").handlers:
        handler.flush()
    scanned = [p for p in home.home.rglob("*") if p.is_file()]
    assert any(p.suffix == ".db" for p in scanned) and any(p.name.endswith(".log") for p in scanned)
    for path in scanned:
        assert TOKEN.encode("utf-8") not in path.read_bytes(), path


def test_errors_never_quote_the_token(home):
    enable(home)
    transport = FakeTransport([HttpResponse(401, {}, f"auth_invalid for {TOKEN}".encode("utf-8"))])
    with pytest.raises(AuthError) as exc:
        service(home, transport).refresh(request())
    assert TOKEN not in str(exc.value)


def test_log_redaction_masks_unregistered_tokens_from_child_loggers(home):
    from wasds150.logging_setup import configure_logging

    configure_logging(home.log_file)
    loose = "rbuapp_NeverRegistered123456"
    logging.getLogger("wasds150.webui").info("header was %s", loose)
    for handler in logging.getLogger("wasds150").handlers:
        handler.flush()
    assert loose not in home.log_file.read_text(encoding="utf-8")


# -- 4. explicit action only ---------------------------------------------------------------------
def test_update_all_makes_zero_repeaterbook_requests(home, monkeypatch):
    import wasds150.update.pipeline as pipeline
    from wasds150.cli import main

    enable(home)
    monkeypatch.setenv(policy.DEFAULT_TOKEN_ENV, TOKEN)  # ready in every respect
    sent = []
    monkeypatch.setattr(client_mod, "urllib_transport", lambda *a, **k: sent.append(a) or ok())
    ran = {}

    def fake_run_sources(sources, http_client=None):
        ran["names"] = [s.name for s in sources]
        return pipeline.UpdateRunResult()

    monkeypatch.setattr(pipeline, "run_sources", fake_run_sources)
    assert main(["--home", str(home.home), "sources", "update", "--offline"]) == 0
    assert ran["names"] and "repeaterbook" not in ran["names"]
    assert sent == []


def test_generic_source_paths_refuse_repeaterbook(home, capsys):
    from wasds150.cli import main
    from wasds150.sources.factory import instantiate_source, runnable_source_names
    from wasds150.sources.repeaterbook import ExplicitOnlyError

    assert "repeaterbook" not in runnable_source_names()
    assert runnable_source_names(only={"repeaterbook"}) == []
    with pytest.raises(ExplicitOnlyError):
        instantiate_source("repeaterbook", SourcesConfig())
    assert main(["--home", str(home.home), "sources", "fetch", "repeaterbook"]) == 1
    assert main(["--home", str(home.home), "sources", "update", "--only", "repeaterbook"]) == 1
    assert "repeaterbook refresh" in capsys.readouterr().err


def test_refresh_is_refused_while_disabled_with_the_pending_approval_message(home):
    transport = FakeTransport()
    with pytest.raises(NotEnabledError) as exc:
        service(home, transport).refresh(request())
    assert "pending RepeaterBook approval" in str(exc.value)
    assert transport.calls == []


def test_refresh_is_refused_without_a_token(home):
    enable(home)
    transport = FakeTransport()
    with pytest.raises(TokenMissingError):
        service(home, transport, token=None).refresh(request())
    assert transport.calls == []


def test_status_is_ready_only_with_both_the_flag_and_a_token(home):
    assert not service(home).status()["ready"]
    assert service(home).status()["message"] == policy.PENDING_APPROVAL_MESSAGE
    enable(home)
    assert not service(home, token=None).status()["ready"]
    assert service(home).status()["ready"]


def test_the_ui_lists_repeaterbook_but_greys_out_refresh_until_ready():
    static = REPO_ROOT / "src" / "wasds150" / "webui" / "static"
    page = (static / "index.html").read_text(encoding="utf-8")
    script = (static / "app.js").read_text(encoding="utf-8")
    assert '<button id="rb-refresh-btn" disabled>' in page
    assert 'getElementById("rb-refresh-btn").disabled = !s.ready' in script


def test_normal_radio_export_never_calls_repeaterbook(home, tmp_path):
    from wasds150.appctx import build_context
    from wasds150.plan.service import export_plan

    enable(home)
    transport = FakeTransport([ok([record(1, freq=146.955)])])
    svc = service(home, transport)
    svc.refresh(request())
    svc.apply()
    ctx = build_context(home)
    # The autouse fixture fails the test if anything reaches the real transport.
    plain = export_plan(ctx, "h9-ozette", out_dir=tmp_path / "plain")
    assert "RB01" not in plain.report_path.read_text(encoding="utf-8")
    assert "146.955" not in plain.csv_path.read_text(encoding="utf-8")
    assert len(transport.calls) == 1


# -- 5. never parallel ----------------------------------------------------------------------------
def test_a_second_refresh_while_one_runs_is_refused(home):
    enable(home)
    transport = FakeTransport()
    svc = service(home, transport)
    with svc.store.action_lock(T0):
        with pytest.raises(ActionInProgress):
            svc.refresh(request())
    assert transport.calls == []


def test_another_process_lock_is_respected_and_a_stale_one_cleared(home):
    enable(home)
    transport = FakeTransport()
    svc = service(home, transport)
    svc.store.root.mkdir(parents=True, exist_ok=True)
    svc.store.lock_path.write_text("1 other-process", encoding="utf-8")
    with pytest.raises(ActionInProgress):
        svc.refresh(request())
    stale = time.time() - 16 * 60
    os.utime(svc.store.lock_path, (stale, stale))
    svc.refresh(request())
    assert len(transport.calls) == 1 and not svc.store.lock_path.exists()


def test_regions_are_requested_one_at_a_time_in_order(home):
    enable(home)
    transport = FakeTransport()
    service(home, transport).refresh(request(("WA", "OR", "ID")))
    assert transport.max_in_flight == 1
    assert [dict(parse_qsl(urlsplit(c["url"]).query))["state_id"] for c in transport.calls] == ["53", "41", "16"]


# -- 6. request limits ----------------------------------------------------------------------------------
def test_exactly_one_request_per_region(home):
    enable(home)
    transport = FakeTransport()
    result = service(home, transport).refresh(request(("WA", "OR")))
    assert len(transport.calls) == 2 and result["requests_sent"] == 2


def test_the_same_region_is_not_requested_again_within_60_minutes(home):
    enable(home)
    clock, transport = Clock(), FakeTransport()
    svc = service(home, transport, clock)
    svc.refresh(request())
    clock.advance(minutes=59)
    with pytest.raises(LimitError):
        svc.refresh(request())
    assert len(transport.calls) == 1
    clock.advance(minutes=1)
    svc.refresh(request())
    assert len(transport.calls) == 2


def test_at_most_four_requests_in_any_rolling_24_hours(home):
    enable(home)
    clock, transport = Clock(), FakeTransport()
    svc = service(home, transport, clock)
    svc.refresh(request(("WA", "OR", "ID")))
    clock.advance(minutes=61)
    svc.refresh(request(("WA",)))
    clock.advance(minutes=61)
    with pytest.raises(LimitError):
        svc.refresh(request(("OR",)))
    assert len(transport.calls) == 4
    clock.now = T0 + datetime.timedelta(hours=24, minutes=1)
    svc.refresh(request(("OR",)))
    assert len(transport.calls) == 5


def test_the_budget_is_checked_for_every_region_before_anything_is_sent(home):
    enable(home)
    clock, transport = Clock(), FakeTransport()
    svc = service(home, transport, clock)
    svc.refresh(request(("WA", "OR", "ID")))
    clock.advance(minutes=61)
    with pytest.raises(LimitError) as exc:
        svc.refresh(request(("WA", "OR")))  # needs 2, only 1 remains
    assert "Nothing was sent" in str(exc.value)
    assert len(transport.calls) == 3


def test_delete_all_does_not_reset_the_request_budget(home):
    enable(home)
    clock, transport = Clock(), FakeTransport()
    svc = service(home, transport, clock)
    svc.refresh(request(("WA", "OR", "ID")))
    svc.delete_all()
    clock.advance(minutes=61)
    with pytest.raises(LimitError):
        svc.refresh(request(("WA", "OR")))
    assert len(transport.calls) == 3


# -- 7. geography and bands ----------------------------------------------------------------------
def test_region_allowlist_and_its_verified_parameters():
    assert set(policy.REGIONS) == {"WA", "OR", "ID", "BC"}
    assert {code: r.state_id for code, r in policy.REGIONS.items() if r.verified} == {"WA": "53", "OR": "41", "ID": "16"}
    assert not policy.REGIONS["BC"].verified and policy.REGIONS["BC"].state_id is None


@pytest.mark.parametrize(
    "regions, message",
    [
        (("BC",), "not enabled"),
        (("CA",), "not on the allowlist"),
        (("WA", "WA"), "only once"),
        (("WA", "OR", "ID", "BC"), "at most 3"),
        ((), "at least one region"),
    ],
)
def test_regions_outside_the_policy_are_refused_before_sending(home, regions, message):
    enable(home)
    transport = FakeTransport()
    with pytest.raises(PolicyError, match=message):
        service(home, transport).refresh(request(regions))
    assert transport.calls == []


@pytest.mark.parametrize("radius", [0, 61, -1, 1.5, True, "60", None])
def test_radius_must_be_a_whole_number_from_1_to_60(radius):
    with pytest.raises(PolicyError):
        validate_request(request(radius=radius))


@pytest.mark.parametrize("radius", [1, 60])
def test_radius_bounds_are_inclusive(radius):
    validate_request(request(radius=radius))


def test_exactly_one_valid_centre_is_required():
    for center in [(95.0, 0.0), (0.0, 200.0), (float("nan"), 0.0), ()]:
        with pytest.raises(PolicyError):
            validate_request(RefreshRequest(("WA",), center, 60, ("2m",), "th-d75"))


def test_bands_must_be_known_and_supported_by_the_radio():
    with pytest.raises(PolicyError, match="unknown band"):
        validate_request(request(bands=("11m",)))
    with pytest.raises(PolicyError, match="does not support"):
        validate_request(request(bands=("23cm",), radio="td-h9"))
    with pytest.raises(PolicyError, match="at least one band"):
        validate_request(request(bands=()))


def test_distance_is_great_circle():
    seattle, portland = (47.6062, -122.3321), (45.5152, -122.6784)
    assert abs(great_circle_miles(seattle, portland) - 145.1) < 1.5


def test_local_filtering_drops_rather_than_coerces(home):
    enable(home)
    records = [
        record(1),  # kept
        record(2, lat=45.0),  # ~180 mi away
        record(3, freq=52.5),  # 6 m, not selected
        record(4, Lat="", Long=""),  # no coordinates
        record(5, lat=0, lon=0),  # null island
        record(6, analog="No"),  # digital only
        record(7, **{"Frequency": ""}),  # no output frequency
    ]
    result = service(home, FakeTransport([ok(records)])).refresh(request())
    assert [c["rb_key"] for c in result["candidates"]] == ["53:1001"]
    assert result["drops"] == {
        "no usable coordinates": 2,
        "no usable output frequency": 1,
        "not analog FM (digital-only repeaters are dropped, never coerced)": 1,
        "outside the radius": 1,
        "outside the selected bands": 1,
    }


def test_missing_input_tone_or_offset_is_never_synthesized(home):
    enable(home)
    svc = service(home, FakeTransport([ok([record(1, input_freq="", pl="", tsq="")])]))
    (candidate,) = svc.refresh(request())["candidates"]
    assert candidate["input_mhz"] is None and candidate["tx_tone"] == "" and candidate["rx_tone"] == ""
    assert "no-input-published" in candidate["flags"]
    assert svc.apply()["applied"] == 0  # flagged: needs explicit review
    svc_again = service(home, FakeTransport(), svc.clock)
    assert svc_again.apply(include_flagged=True)["applied"] == 1
    channel = svc_again.reviewed_favorite().systems[0].departments[0].channels[0]
    assert channel.tx_freq_mhz is None and channel.tx_tone == ""


def test_staging_review_apply_carries_source_id_date_and_attribution(home):
    enable(home)
    svc = service(home, FakeTransport([ok([record(1, pl="103.5")])]))
    svc.refresh(request())
    assert svc.records()["records"] == []  # nothing applies until reviewed and applied
    assert svc.apply()["applied"] == 1
    (applied,) = svc.records()["records"]
    assert applied["rb_key"] == "53:1001" and applied["retrieved_at"].startswith("2026-09-10")
    channel = svc.reviewed_favorite().systems[0].departments[0].channels[0]
    assert "RepeaterBook record 53:1001, retrieved 2026-09-10" in channel.notes
    assert "Data courtesy of RepeaterBook.com" in channel.notes
    assert channel.tx_tone == "TONE=C103.5"


def test_offline_refilter_reuses_fresh_cache_without_a_request(home):
    enable(home)
    transport = FakeTransport()
    clock = Clock()
    svc = service(home, transport, clock)
    svc.refresh(request())
    enable(home, False)
    result = svc.refresh(request(radius=5), offline=True)
    assert result["requests_sent"] == 0 and len(transport.calls) == 1
    clock.advance(days=7)
    with pytest.raises(PolicyError, match="under 7 days"):
        svc.refresh(request(), offline=True)


# -- 8. candidate cap -----------------------------------------------------------------------------
def test_251_candidates_fail_closed_and_import_nothing(home):
    enable(home)
    svc = service(home, FakeTransport([ok([record(i) for i in range(251)])]))
    with pytest.raises(CandidateCapError):
        svc.refresh(request())
    assert svc.staged()["candidates"] == []


def test_250_candidates_are_staged(home):
    enable(home)
    svc = service(home, FakeTransport([ok([record(i) for i in range(250)])]))
    assert len(svc.refresh(request())["candidates"]) == 250


def test_the_cap_applies_to_the_combined_regions(home):
    enable(home)
    wa = ok([record(i) for i in range(130)])
    oregon = ok([record(i, state_id="41") for i in range(130)])
    svc = service(home, FakeTransport([wa, oregon]))
    with pytest.raises(CandidateCapError, match="260"):
        svc.refresh(request(("WA", "OR")))
    assert svc.staged()["candidates"] == []


# -- 9. no pagination ---------------------------------------------------------------------------------
def test_a_request_carries_only_the_region_parameters(home):
    enable(home)
    transport = FakeTransport()
    service(home, transport).refresh(request())
    parts = urlsplit(transport.calls[0]["url"])
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == policy.EXPORT_ENDPOINT
    assert parse_qsl(parts.query) == [("country", "United States"), ("state_id", "53")]
    assert build_export_url(policy.REGIONS["WA"]) == (
        "https://www.repeaterbook.com/api/export.php?country=United%20States&state_id=53"
    )


# -- 10. errors, 429 and no retry ------------------------------------------------------------------------
@pytest.mark.parametrize("retry_after, locked_minutes", [(None, 60), ("120", 60), ("7200", 120)])
def test_429_locks_refresh_until_the_later_of_retry_after_and_60_minutes(home, retry_after, locked_minutes):
    enable(home)
    clock = Clock()
    headers = {"Retry-After": retry_after} if retry_after else {}
    transport = FakeTransport([HttpResponse(429, headers, b"")])
    svc = service(home, transport, clock)
    with pytest.raises(RateLimited):
        svc.refresh(request())
    assert len(transport.calls) == 1  # no same-action retry
    clock.advance(minutes=locked_minutes - 1)
    with pytest.raises(LimitError, match="locked until"):
        svc.refresh(request(("OR",)))
    assert len(transport.calls) == 1
    clock.advance(minutes=1, seconds=1)
    svc.refresh(request(("OR",)))
    assert len(transport.calls) == 2


def test_retry_after_as_an_http_date():
    assert parse_retry_after("Thu, 10 Sep 2026 14:00:00 GMT", T0) == datetime.timedelta(hours=2)
    assert parse_retry_after("soon", T0) is None


def test_a_429_mid_action_stops_the_remaining_regions(home):
    enable(home)
    transport = FakeTransport([ok(), HttpResponse(429, {}, b""), ok()])
    svc = service(home, transport)
    with pytest.raises(RateLimited):
        svc.refresh(request(("WA", "OR", "ID")))
    assert len(transport.calls) == 2
    assert svc.staged()["candidates"] == []


@pytest.mark.parametrize(
    "status, payload",
    [
        (401, b""),
        (403, b""),
        (200, b'{"error": "auth_revoked"}'),
        (403, b'{"error": {"code": "ua_mismatch"}}'),
        (403, b"auth_scope_denied"),
    ],
)
def test_auth_scope_and_user_agent_errors_block_until_the_operator_acts(home, status, payload):
    enable(home)
    clock = Clock()
    transport = FakeTransport([HttpResponse(status, {}, payload)])
    svc = service(home, transport, clock)
    with pytest.raises(AuthError):
        svc.refresh(request())
    clock.advance(minutes=61)
    with pytest.raises(LimitError, match="unblock"):
        svc.refresh(request(("OR",)))
    assert len(transport.calls) == 1  # never retried
    assert svc.unblock_auth() is True
    svc.refresh(request(("OR",)))
    assert len(transport.calls) == 2


@pytest.mark.parametrize("status", [408, 425, 500, 502, 503, 504])
def test_transient_errors_stop_without_retry(home, status):
    enable(home)
    transport = FakeTransport([HttpResponse(status, {}, b"")])
    with pytest.raises(TransientError):
        service(home, transport).refresh(request())
    assert len(transport.calls) == 1


@pytest.mark.parametrize("status", [400, 404])
def test_bad_filter_or_endpoint_stops(home, status):
    enable(home)
    with pytest.raises(BadRequest):
        service(home, FakeTransport([HttpResponse(status, {}, b"")])).refresh(request())


def test_redirects_are_refused_so_the_token_cannot_follow_one():
    with pytest.raises(ResponseError):
        classify(HttpResponse(302, {"Location": "https://elsewhere.example/"}, b""), T0)
    assert client_mod._RefuseRedirects().redirect_request(None, None, 302, "", {}, "https://x") is None


def test_a_response_that_is_not_the_export_shape_imports_nothing(home):
    from wasds150.sources.repeaterbook.normalize import ResponseShapeError

    enable(home)
    svc = service(home, FakeTransport([HttpResponse(200, {}, b"<html>not json</html>")]))
    with pytest.raises(ResponseShapeError):
        svc.refresh(request())
    assert svc.staged()["candidates"] == []


# -- 11. retention and deletion ---------------------------------------------------------------------------
def test_raw_is_fresh_for_7_days_after_which_it_cannot_be_applied(home):
    enable(home)
    clock = Clock()
    svc = service(home, FakeTransport(), clock)
    svc.refresh(request())
    clock.advance(days=7)
    result = svc.apply()
    assert result["applied"] == 0 and "older than 7 days" in result["skipped"][0]["reason"]
    assert next(r for r in svc.status()["regions"] if r["code"] == "WA")["cache"] == "stale"


def test_raw_responses_and_staging_are_deleted_by_day_30(home):
    enable(home)
    clock = Clock()
    svc = service(home, FakeTransport(), clock)
    svc.refresh(request())
    assert list(svc.store.raw_dir.iterdir())
    clock.advance(days=29, hours=23)
    svc.purge()
    assert list(svc.store.raw_dir.iterdir()) and svc.staged()["candidates"]
    clock.advance(hours=1)
    svc.purge()
    assert list(svc.store.raw_dir.iterdir()) == []
    assert svc.staged()["candidates"] == [] and svc.store.latest_raw_meta("WA") is None


def test_applied_records_are_deleted_by_day_90_unless_reviewed_again(home):
    enable(home)
    clock = Clock()
    first = ok([record(1), record(2)])
    second = ok([record(1)])
    svc = service(home, FakeTransport([first, second]), clock)
    svc.refresh(request())
    svc.apply()
    clock.advance(days=60)
    svc.refresh(request())
    svc.apply()  # record 1 reviewed again on day 60
    clock.advance(days=30)  # day 90 for record 2
    assert [r["rb_key"] for r in svc.records()["records"]] == ["53:1001"]


def test_purges_run_before_a_refresh_and_at_startup(home):
    enable(home)
    clock = Clock()
    svc = service(home, FakeTransport(), clock)
    svc.store.put_raw("OR", b"{}", T0 - datetime.timedelta(days=31))
    svc.refresh(request())
    assert svc.store.latest_raw_meta("OR") is None
    svc.store.put_raw("OR", b"{}", T0 - datetime.timedelta(days=31))
    purge_on_startup(home, clock)
    assert svc.store.latest_raw_meta("OR") is None


def test_cli_startup_purges_expired_data(home):
    from wasds150.cli import main

    store = RepeaterBookStore.for_config(home)
    store.put_raw("WA", b"{}", datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=31))
    assert main(["--home", str(home.home), "repeaterbook", "regions"]) == 0
    assert store.latest_raw_meta("WA") is None


def test_delete_all_removes_blobs_rows_ledger_and_reports(home, tmp_path):
    enable(home)
    svc = service(home, FakeTransport())
    svc.refresh(request())
    svc.apply()
    report = svc.write_review_report("md")
    elsewhere = tmp_path / "exports" / "plan-report.md"
    elsewhere.parent.mkdir()
    elsewhere.write_text("RepeaterBook-derived rows", encoding="utf-8")
    svc.register_export_report(elsewhere)
    assert list(svc.store.raw_dir.iterdir()) and svc.store.ledger()

    counts = svc.delete_all()

    assert counts["raw"] == 1 and counts["derived"] == 1 and counts["reports"] == 2
    assert not svc.store.raw_dir.exists() and not svc.store.db_path.exists()
    assert not report.exists() and not elsewhere.exists()
    assert svc.records()["records"] == [] and svc.store.ledger() == [] and svc.staged()["candidates"] == []
    assert svc.status()["token_configured"]  # deleting the token is a separate action


def test_forget_token_is_a_separate_action(home):
    svc = service(home)
    svc.configure(token_env="MY_RB_TOKEN")
    svc.delete_all()
    assert SourcesConfig.load(home.sources_config_path).repeaterbook_token_env == "MY_RB_TOKEN"
    svc.forget_token()
    assert SourcesConfig.load(home.sources_config_path).repeaterbook_token_env is None


# -- 12. generated files -------------------------------------------------------------------------------
def test_export_with_repeaterbook_holds_only_programming_fields(home, tmp_path):
    from wasds150.appctx import build_context
    from wasds150.plan.service import export_plan

    enable(home)
    svc = service(home, FakeTransport([ok([record(1, freq=146.955, Notes="raw note")])]))
    svc.refresh(request())
    svc.apply()
    exported = export_plan(build_context(home), "h9-ozette", out_dir=tmp_path / "out", with_repeaterbook=True)
    text = exported.csv_path.read_text(encoding="utf-8")
    assert "146.955000" in text and "RepeaterBook record 53:1001" in text
    for raw_only in ("Rptr ID", "results", "raw note", "Last Update", TOKEN):
        assert raw_only not in text
    assert not home.catalog_path.exists() or "RB01" not in home.catalog_path.read_text(encoding="utf-8")


def test_repeaterbook_records_never_go_into_a_redistributable_export(home, tmp_path):
    from wasds150.appctx import build_context
    from wasds150.plan.service import export_plan

    with pytest.raises(ValueError, match="redistributable"):
        export_plan(build_context(home), "h9-ozette", out_dir=tmp_path, include_licensed=False, with_repeaterbook=True)


def test_the_reviewed_list_is_licensed_so_committable_exports_exclude_it(home):
    enable(home)
    svc = service(home, FakeTransport())
    svc.refresh(request())
    svc.apply()
    assert svc.reviewed_favorite().licensed is True


# -- 13. attribution ----------------------------------------------------------------------------------------
def test_attribution_appears_in_every_output(home, tmp_path, capsys):
    from wasds150.appctx import build_context
    from wasds150.plan.service import export_plan

    enable(home)
    svc = service(home, FakeTransport([ok([record(1, freq=146.955)])]))
    refreshed = svc.refresh(request())
    assert "Data courtesy of RepeaterBook.com <https://www.repeaterbook.com/>" in format_preview(refreshed)
    for payload in (refreshed, svc.staged(), svc.status(), svc.apply(), svc.records()):
        assert payload["attribution"] == {"text": policy.ATTRIBUTION_TEXT, "url": policy.ATTRIBUTION_URL}
    assert ATTRIBUTION_MD in svc.write_review_report("md").read_text(encoding="utf-8")
    assert (
        '<a href="https://www.repeaterbook.com/">Data courtesy of RepeaterBook.com</a>'
        in svc.write_review_report("html").read_text(encoding="utf-8")
    )
    exported = export_plan(build_context(home), "h9-ozette", out_dir=tmp_path / "out", with_repeaterbook=True)
    report = exported.report_path.read_text(encoding="utf-8")
    assert "## Source attribution" in report and ATTRIBUTION_MD in report
    page = (REPO_ROOT / "src" / "wasds150" / "webui" / "static" / "index.html").read_text(encoding="utf-8")
    assert '<a href="https://www.repeaterbook.com/" target="_blank" rel="noopener">Data courtesy of RepeaterBook.com</a>' in page


def test_detail_links_use_the_home_page_until_the_url_form_is_confirmed(monkeypatch):
    import wasds150.sources.repeaterbook.catalog as catalog

    assert detail_url("53", "1001") == policy.ATTRIBUTION_URL
    monkeypatch.setattr(catalog, "DETAIL_URL_CONFIRMED", True)
    assert catalog.detail_url("53", "1001") == policy.DETAIL_URL_TEMPLATE.format(state_id="53", rb_id="1001")


def test_html_report_escapes_third_party_text(home):
    enable(home)
    svc = service(home, FakeTransport([ok([record(1, **{"Nearest City": "<script>x</script>"})])]))
    svc.refresh(request())
    html_text = svc.write_review_report("html").read_text(encoding="utf-8")
    assert "<script>x</script>" not in html_text and "&lt;script&gt;" in html_text


# -- 14. never committed ------------------------------------------------------------------------------------
def test_everything_lives_under_the_local_state_directory(home):
    assert RepeaterBookStore.for_config(home).root == home.state_dir / "repeaterbook"


def test_the_in_repo_working_home_is_git_ignored():
    lines = {line.strip().rstrip("/") for line in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    assert ".wasds150-home" in lines


# -- CLI and web UI ------------------------------------------------------------------------------------------
def test_cli_flow(home, monkeypatch, capsys):
    from wasds150.cli import main

    transport = FakeTransport()
    monkeypatch.setattr(client_mod, "urllib_transport", transport)
    monkeypatch.setenv(policy.DEFAULT_TOKEN_ENV, TOKEN)
    h = ["--home", str(home.home), "repeaterbook"]
    assert main(h + ["refresh", "--regions", "WA", "--center", "47.633,-121.966", "--bands", "2m", "--radio", "th-d75"]) == 1
    assert "pending RepeaterBook approval" in capsys.readouterr().err
    assert main(h + ["configure", "--enable"]) == 0
    assert main(h + ["refresh", "--regions", "WA", "--center", "47.633,-121.966", "--bands", "2m", "--radio", "th-d75"]) == 0
    assert main(h + ["review", "--report", "md"]) == 0
    assert main(h + ["apply"]) == 0
    assert main(h + ["records"]) == 0
    assert main(h + ["status"]) == 0
    out = capsys.readouterr().out
    assert out.count("Data courtesy of RepeaterBook.com") >= 4
    assert TOKEN not in out
    assert main(h + ["delete-all"]) == 1
    assert main(h + ["delete-all", "--yes"]) == 0
    assert len(transport.calls) == 1


def _call(router, method, path, payload=None):
    from wasds150.webui.router import RequestContext

    handler, params = router.resolve(method, path)
    data = json.dumps(payload).encode("utf-8") if payload is not None else b""
    response = handler(RequestContext(method, path, params, {}, data, {}))
    return response.status, json.loads(response.body)


def test_web_routes(home, monkeypatch):
    from wasds150.appctx import build_context
    from wasds150.webui.api import build_router

    transport = FakeTransport()
    monkeypatch.setattr(client_mod, "urllib_transport", transport)
    monkeypatch.setenv(policy.DEFAULT_TOKEN_ENV, TOKEN)
    router = build_router(build_context(home))
    body = {"regions": "WA", "center": "47.633,-121.966", "radius_mi": 60, "bands": "2m,70cm", "radio": "th-d75"}

    assert _call(router, "POST", "/api/v1/repeaterbook/refresh", body)[0] == 403
    assert _call(router, "POST", "/api/v1/repeaterbook/configure", {"token": TOKEN})[0] == 400
    status, data = _call(router, "POST", "/api/v1/repeaterbook/configure", {"enabled": True})
    assert status == 200 and data["ready"] is True
    status, data = _call(router, "POST", "/api/v1/repeaterbook/refresh", body)
    assert status == 200 and data["attribution"]["url"] == policy.ATTRIBUTION_URL
    assert _call(router, "POST", "/api/v1/repeaterbook/refresh", body)[0] == 409  # 60-minute cooldown
    assert _call(router, "GET", "/api/v1/repeaterbook/staged")[1]["candidates"]
    assert _call(router, "POST", "/api/v1/repeaterbook/apply", {})[1]["applied"] == 1
    records = _call(router, "GET", "/api/v1/repeaterbook/records")[1]
    assert records["records"][0]["detail_url"] and records["attribution"]["text"] == policy.ATTRIBUTION_TEXT
    assert _call(router, "POST", "/api/v1/sources/fetch", {"name": "repeaterbook"})[0] == 400
    assert _call(router, "POST", "/api/v1/sources/update", {"only": ["repeaterbook"]})[0] == 400
    listed = {s["name"]: s for s in _call(router, "GET", "/api/v1/sources")[1]["sources"]}
    assert listed["repeaterbook"]["explicit_only"] is True
    assert _call(router, "POST", "/api/v1/repeaterbook/delete-all", {})[0] == 400
    assert _call(router, "POST", "/api/v1/repeaterbook/delete-all", {"confirm": "DELETE"})[0] == 200
    assert len(transport.calls) == 1
    for status_body in (_call(router, "GET", "/api/v1/repeaterbook/status")[1],):
        assert TOKEN not in json.dumps(status_body)
