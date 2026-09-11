"""Web API for the fleet: status, settings, update jobs, zip downloads."""
from __future__ import annotations

import io
import json
import threading
import time
import urllib.error
import urllib.request
import zipfile

import pytest

from conftest import REPO_CSV_PATH
from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.webui.server import build_server


@pytest.fixture()
def live(tmp_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    ctx = build_context(config, csv_override=REPO_CSV_PATH)
    server, token = build_server(ctx, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[0], server.server_address[1]
    try:
        yield f"http://{host}:{port}", token, ctx
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _call(live, path, method="GET", body=None):
    base, token, _ = live
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("X-Wasds150-Token", token)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def _json(live, path, method="GET", body=None):
    status, raw, _ = _call(live, path, method, body)
    return status, json.loads(raw)


def test_fleet_lists_every_radio_and_the_sources(live):
    status, data = _json(live, "/api/v1/fleet")
    assert status == 200
    assert [r["radio_id"] for r in data["radios"]] == [
        "sds150", "td-h9", "th-d75", "ftx1", "at-d890uv", "id-52a"
    ]
    assert all(r["status"]["stale"] for r in data["radios"])
    assert any(s["name"] == "noaa_nwr" for s in data["sources"])


def test_settings_are_saved_and_validated(live):
    status, data = _json(live, "/api/v1/fleet/settings", "POST", {"set": {"td-h9.com_port": "COM7"}})
    assert status == 200 and data["radios"]["td-h9"]["values"]["com_port"] == "COM7"
    status, data = _json(live, "/api/v1/fleet/settings", "POST", {"set": {"td-h9.baud": "38400"}})
    assert status == 400


def test_a_dry_run_update_runs_as_a_job(live, tmp_path):
    body = {"radio_ids": ["td-h9"], "refresh_sources": False, "out_dir": str(tmp_path / "out")}
    status, data = _json(live, "/api/v1/fleet/update", "POST", body)
    assert status == 202
    job_id = data["job_id"]
    deadline = time.monotonic() + 120
    while True:
        _, job = _json(live, f"/api/v1/jobs/{job_id}")
        if job["status"] not in ("queued", "running", "waiting"):
            break
        assert time.monotonic() < deadline
        time.sleep(0.1)
    assert job["status"] == "finished", job["error"]
    _, events = _json(live, f"/api/v1/jobs/{job_id}/events?since=0")
    assert events["events"][0]["kind"] == "job.started"
    _, later = _json(live, f"/api/v1/jobs/{job_id}/events?since={events['last_seq']}")
    assert later["events"] == []
    status, _ = _json(live, f"/api/v1/jobs/{job_id}/answer", "POST", {"step_id": "x", "decision": "done"})
    assert status == 409
    _, jobs = _json(live, "/api/v1/jobs")
    assert jobs["jobs"][0]["job_id"] == job_id


def test_bad_update_requests_are_rejected(live):
    assert _json(live, "/api/v1/fleet/update", "POST", {"radio_ids": ["ic-705"]})[0] == 400
    assert _json(live, "/api/v1/fleet/update", "POST", {"radio_ids": []})[0] == 400
    assert _json(live, "/api/v1/jobs/nope")[0] == 404
    assert _json(live, "/api/v1/jobs/nope/events?since=x")[0] == 400


def test_plan_zip_download(live):
    status, raw, headers = _call(live, "/api/v1/plans/td-h9-fleet/export.zip")
    assert status == 200
    assert headers["Content-Type"] == "application/zip"
    assert 'filename="td-h9-fleet.zip"' in headers["Content-Disposition"]
    names = zipfile.ZipFile(io.BytesIO(raw)).namelist()
    assert set(names) == {"td-h9-fleet.csv", "td-h9-fleet-report.md"}
    status, raw, _ = _call(live, "/api/v1/plans/at-d890uv-fleet/export.zip")
    assert status == 200
    assert "at-d890uv-fleet/Channel.CSV" in zipfile.ZipFile(io.BytesIO(raw)).namelist()
    assert _call(live, "/api/v1/plans/no-such-plan/export.zip")[0] == 404


def test_loadout_detail_says_how_the_radio_is_loaded(live):
    _, detail = _json(live, "/api/v1/loadouts/td-h9-fleet")
    assert detail["fleet"]["load_path"] == "automated"
    _, detail = _json(live, "/api/v1/loadouts/at-d890uv-fleet")
    assert detail["fleet"]["load_path"] == "prepare-and-guide"


def test_the_page_has_a_fleet_tab(live):
    base, _, _ = live
    with urllib.request.urlopen(base + "/") as resp:
        assert b'data-tab="fleet"' in resp.read()
    with urllib.request.urlopen(base + "/app.js") as resp:
        script = resp.read()
    assert b"function loadFleet" in script
    assert b'currentPlanDetail.radio_id !== "td-h9"' not in script


def test_a_server_start_marks_orphaned_jobs_interrupted(tmp_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    orphan = {
        "job_id": "20260910-000000-abcdef", "kind": "fleet-update", "title": "left behind",
        "status": "waiting", "created_at": "2026-09-10T00:00:00+00:00", "last_seq": 3, "steps": [],
    }
    (config.jobs_dir / f"{orphan['job_id']}.json").write_text(json.dumps(orphan), encoding="utf-8")
    ctx = build_context(config, csv_override=REPO_CSV_PATH)
    server, _token = build_server(ctx, port=0)
    server.server_close()
    saved = json.loads((config.jobs_dir / f"{orphan['job_id']}.json").read_text(encoding="utf-8"))
    assert saved["status"] == "interrupted"
