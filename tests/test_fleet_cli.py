"""CLI for the fleet: list, describe, settings, status, export, docs."""
from __future__ import annotations

import json

from conftest import REPO_ROOT
from wasds150 import cli
from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.fleet.service import fleet_status, record_sync


def run(argv):
    return cli.main(argv)


def test_fleet_list_json(wasds_home, sample_csv_path, capsys):
    assert run(["--csv", str(sample_csv_path), "fleet", "list", "--json"]) == 0
    radios = json.loads(capsys.readouterr().out)["radios"]
    assert [r["radio_id"] for r in radios] == ["sds150", "td-h9", "th-d75", "ftx1", "at-d890uv"]
    assert radios[1]["plan_id"] == "td-h9-fleet"


def test_fleet_describe_markdown_and_unknown(wasds_home, capsys):
    assert run(["fleet", "describe", "td-h9", "--markdown"]) == 0
    out = capsys.readouterr().out
    assert "1. **Connect the radio** _(confirm)_" in out
    assert run(["fleet", "describe", "ic-705"]) == 1


def test_fleet_settings_set_and_reject(wasds_home, capsys):
    assert run(["fleet", "settings", "--set", "td-h9.com_port=COM7", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["radios"]["td-h9"]["values"]["com_port"] == "COM7"
    assert data["radios"]["td-h9"]["missing"] == []
    assert run(["fleet", "settings", "--set", "td-h9.baud=38400"]) == 1
    assert run(["fleet", "settings", "--set", "nonsense"]) == 1


def test_fleet_status_marks_unsynced_radios_and_clears_after_a_sync(wasds_home, sample_csv_path, capsys):
    assert run(["--csv", str(sample_csv_path), "fleet", "status", "--json"]) == 0
    radios = json.loads(capsys.readouterr().out)["radios"]
    assert all(r["stale"] and r["reasons"] == ["never synced"] for r in radios)

    ctx = build_context(AppConfig.default(), csv_override=sample_csv_path)
    record_sync(ctx, "td-h9", job_id="test")
    by_radio = {s.radio_id: s for s in fleet_status(ctx)}
    assert not by_radio["td-h9"].stale
    assert by_radio["ftx1"].stale


def test_fleet_export_writes_each_radio(wasds_home, sample_csv_path, tmp_path, capsys):
    out = tmp_path / "out"
    code = run(
        ["--csv", str(sample_csv_path), "fleet", "export", "--radios", "td-h9,sds150", "--out", str(out), "--json"]
    )
    assert code == 0
    exports = {e["radio_id"]: e for e in json.loads(capsys.readouterr().out)["exports"]}
    assert exports["td-h9"]["path"].endswith("td-h9-fleet.csv")
    assert (out / "td-h9-fleet.csv").is_file()
    assert (out / "td-h9-fleet-report.md").is_file()
    assert len(exports["td-h9"]["sha256"]) == 64
    assert (out / "sds150" / "favorites-overview.md").is_file()


def test_fleet_export_unknown_radio_fails_cleanly(wasds_home, sample_csv_path, tmp_path, capsys):
    code = run(["--csv", str(sample_csv_path), "fleet", "export", "--radios", "ic-705", "--out", str(tmp_path)])
    assert code == 1
    assert "unknown fleet radio" in capsys.readouterr().err


def test_fleet_docs_check_passes_on_the_committed_docs(capsys):
    assert run(["fleet", "docs", "--check", "--root", str(REPO_ROOT)]) == 0
