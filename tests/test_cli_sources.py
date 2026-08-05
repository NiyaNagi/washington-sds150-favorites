"""CLI tests for the ``sources`` subcommand group (list/status/configure/
fetch/update/provenance). ``fetch``/``update`` are exercised only against
offline-cache-miss failure paths and pure-local (Sentinel/RR) sources, so
none of these tests touch the network.
"""
from __future__ import annotations

import json
import os
import stat

from wasds150 import cli


def run(argv):
    return cli.main(argv)


def test_sources_list_json(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "sources", "list", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    names = {s["name"] for s in data["sources"]}
    assert "wwara" in names
    assert "static_pack" in names
    assert "sentinel_local" in names


def test_sources_status_json(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "sources", "status", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["offline"] is False
    assert any(s["name"] == "wwara" for s in data["sources"])


def test_sources_configure_persists_and_has_restrictive_perms(wasds_home, sample_csv_path, capsys, tmp_path):
    code = run(
        [
            "--csv",
            str(sample_csv_path),
            "sources",
            "configure",
            "--offline",
            "--rr-username",
            "myuser",
            "--rr-app-key",
            "mykey",
            "--json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["offline"] is True
    assert data["radioreference_configured"] is True

    config_path = wasds_home / "state" / "sources.json"
    assert config_path.exists()
    saved = json.loads(config_path.read_text())
    assert saved["offline"] is True
    assert saved["radioreference_username"] == "myuser"
    # Password is never a field at all -- nothing to leak.
    assert "radioreference_password" not in saved
    if os.name == "posix":
        mode = stat.S_IMODE(config_path.stat().st_mode)
        assert mode == 0o600


def test_sources_configure_never_prints_password_like_values(wasds_home, sample_csv_path, capsys):
    run(
        [
            "--csv",
            str(sample_csv_path),
            "sources",
            "configure",
            "--rr-username",
            "myuser",
            "--rr-app-key",
            "supersecretkey",
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert "supersecretkey" not in out


def test_sources_fetch_unconfigured_local_source_fails_cleanly(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "sources", "fetch", "sentinel_local", "--json"])
    assert code == 1
    err = capsys.readouterr().err
    assert "not configured" in err


def test_sources_fetch_offline_facts_source_fails_cleanly(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "sources", "configure", "--offline"])
    capsys.readouterr()
    code = run(["--csv", str(sample_csv_path), "sources", "fetch", "wwara", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert code == 1
    assert data["outcome"]["ok"] is False
    assert "offline" in data["outcome"]["error"].lower()


def test_sources_update_offline_preview_is_safe_noop(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "init"])
    capsys.readouterr()
    code = run(["--csv", str(sample_csv_path), "sources", "update", "--only", "amsat", "--offline", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["applied"] is False
    assert data["merge"]["changes"] == []
    assert data["merge"]["conflicts"] == []
    assert data["run"]["outcomes"][0]["ok"] is False  # offline + no cache


def test_sources_provenance_shows_baseline_provenance(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "init"])
    capsys.readouterr()
    code = run(["--csv", str(sample_csv_path), "sources", "provenance", "fl01", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["slug"] == "fl01"
    assert data["provenance"][0]["source_adapter"] == "static_pack"


def test_sources_provenance_unknown_slug(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "sources", "provenance", "nope"])
    assert code == 1
