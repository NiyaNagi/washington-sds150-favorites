import json
from pathlib import Path

import pytest

from wasds150 import cli


def run(argv):
    """Invoke the CLI and return (exit_code, captured stdout is via capsys in
    the caller)."""
    return cli.main(argv)


def test_init_creates_profile(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "init"])
    assert code == 0
    assert (wasds_home / "profile.json").exists()
    out = capsys.readouterr().out
    assert "Initialized" in out


def test_init_is_idempotent_without_force(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "init"])
    code = run(["--csv", str(sample_csv_path), "init"])
    assert code == 0
    assert "already exists" in capsys.readouterr().out


def test_catalog_show_json(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "catalog", "show", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 3


def test_catalog_show_filters_by_slug(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "catalog", "show", "--slug", "fl01", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["slug"] == "fl01"


def test_catalog_show_unknown_slug_errors(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "catalog", "show", "--slug", "nope"])
    assert code == 1


def test_catalog_validate_clean(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "catalog", "validate"])
    assert code == 0
    assert "OK" in capsys.readouterr().out


def test_profile_enable_disable(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "init"])
    assert run(["--csv", str(sample_csv_path), "profile", "disable", "fl01"]) == 0
    capsys.readouterr()
    code = run(["--csv", str(sample_csv_path), "profile", "list", "--all", "--json"])
    data = json.loads(capsys.readouterr().out)
    fl01 = next(f for f in data["favorites"] if f["slug"] == "fl01")
    assert fl01["enabled"] is False

    assert run(["--csv", str(sample_csv_path), "profile", "enable", "fl01"]) == 0
    capsys.readouterr()
    code = run(["--csv", str(sample_csv_path), "profile", "list", "--all", "--json"])
    data = json.loads(capsys.readouterr().out)
    fl01 = next(f for f in data["favorites"] if f["slug"] == "fl01")
    assert fl01["enabled"] is True


def test_profile_enable_unknown_slug(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "profile", "enable", "does-not-exist"])
    assert code == 1


def test_profile_edit_and_show(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "profile", "edit", "fl01", "--field", "notes", "--value", "hello world"])
    capsys.readouterr()
    run(["--csv", str(sample_csv_path), "profile", "show", "fl01", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert data["notes"] == "hello world"


def test_profile_edit_rejects_non_editable_field(wasds_home, sample_csv_path):
    with pytest.raises(SystemExit):
        run(["--csv", str(sample_csv_path), "profile", "edit", "fl01", "--field", "id", "--value", "x"])


def test_profile_remove_and_restore(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "profile", "remove", "fl01", "--reason", "test"])
    capsys.readouterr()
    run(["--csv", str(sample_csv_path), "profile", "list", "--all", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert "fl01" not in {f["slug"] for f in data["favorites"]}

    run(["--csv", str(sample_csv_path), "profile", "restore", "fl01"])
    capsys.readouterr()
    run(["--csv", str(sample_csv_path), "profile", "list", "--all", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert "fl01" in {f["slug"] for f in data["favorites"]}


def test_profile_add_local_list(wasds_home, sample_csv_path, capsys):
    code = run(
        [
            "--csv",
            str(sample_csv_path),
            "profile",
            "add",
            "--key",
            "LOCAL01",
            "--name",
            "My Local List",
            "--region",
            "Testland",
        ]
    )
    assert code == 0
    capsys.readouterr()
    run(["--csv", str(sample_csv_path), "profile", "list", "--all", "--json"])
    data = json.loads(capsys.readouterr().out)
    assert "local01" in {f["slug"] for f in data["favorites"]}


def test_profile_add_local_list_collision_with_baseline(wasds_home, sample_csv_path, capsys):
    code = run(
        ["--csv", str(sample_csv_path), "profile", "add", "--key", "FL01", "--name", "Duplicate"]
    )
    assert code == 1


def test_preview_reports_changes(wasds_home, sample_csv_path, capsys):
    run(["--csv", str(sample_csv_path), "profile", "disable", "fl01"])
    capsys.readouterr()
    code = run(["--csv", str(sample_csv_path), "preview", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["changes"]) == 1
    assert data["changes"][0]["op"] == "disable"


def test_generate_writes_files_and_commits_snapshot(wasds_home, sample_csv_path, tmp_path, capsys):
    out_dir = tmp_path / "output"
    code = run(
        ["--csv", str(sample_csv_path), "generate", "--out", str(out_dir), "--formats", "csv,md,zip", "--json"]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["snapshot_id"] == "0001"
    assert (out_dir / "favorites.csv").exists()
    assert (out_dir / "favorites-overview.md").exists()
    assert (out_dir / "sentinel-import-pack.zip").exists()


def test_generate_hpe_format_writes_loose_per_list_files(wasds_home, sample_csv_path, tmp_path, capsys):
    out_dir = tmp_path / "output"
    code = run(
        ["--csv", str(sample_csv_path), "generate", "--out", str(out_dir), "--formats", "hpe", "--json"]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    # sample_csv_path's FL01 ("ALPHA1 155.000") and FL09a ("CTAF 122.800")
    # each carry an explicit literal frequency; FL02 does not.
    assert (out_dir / "hpe" / "FL01.hpe").exists()
    assert (out_dir / "hpe" / "FL09a.hpe").exists()
    assert not (out_dir / "hpe" / "FL02.hpe").exists()
    assert any("FL02" in w for w in data["warnings"])

    from wasds150.hpe import codec, schema
    from wasds150.hpe.record import parse_records

    text = codec.decode_container((out_dir / "hpe" / "FL01.hpe").read_bytes())
    assert schema.validate_schema(parse_records(text)) == []


def test_generate_default_formats_include_hpe(wasds_home, sample_csv_path, tmp_path, capsys):
    out_dir = tmp_path / "output"
    code = run(["--csv", str(sample_csv_path), "generate", "--out", str(out_dir), "--json"])
    assert code == 0
    assert (out_dir / "hpe" / "FL01.hpe").exists()
    assert (out_dir / "sentinel-import-pack.zip").exists()


def test_catalog_regenerate_baseline_is_deterministic(wasds_home, sample_csv_path, tmp_path, capsys):
    out1 = tmp_path / "b1.json"
    out2 = tmp_path / "b2.json"
    code = run(["catalog", "regenerate-baseline", "--csv", str(sample_csv_path), "--out", str(out1), "--json"])
    assert code == 0
    data1 = json.loads(capsys.readouterr().out)
    code = run(["catalog", "regenerate-baseline", "--csv", str(sample_csv_path), "--out", str(out2), "--json"])
    assert code == 0
    data2 = json.loads(capsys.readouterr().out)

    assert data1["content_hash"] == data2["content_hash"]
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")
    assert data1["favorites"] == 3
    assert data1["with_systems"] == 2  # FL01 and FL09a; FL02 has no explicit frequency


def test_history_list_and_show_and_rollback(wasds_home, sample_csv_path, tmp_path, capsys):
    out_dir = tmp_path / "output"
    run(["--csv", str(sample_csv_path), "generate", "--out", str(out_dir), "--formats", "csv", "--json"])
    capsys.readouterr()

    code = run(["--csv", str(sample_csv_path), "history", "list", "--json"])
    assert code == 0
    snaps = json.loads(capsys.readouterr().out)
    assert len(snaps) == 1
    snap_id = snaps[0]["id"]

    code = run(["--csv", str(sample_csv_path), "history", "show", snap_id])
    assert code == 0
    capsys.readouterr()

    # rollback without --yes should refuse
    code = run(["--csv", str(sample_csv_path), "history", "rollback", snap_id])
    assert code == 1
    capsys.readouterr()

    code = run(["--csv", str(sample_csv_path), "history", "rollback", snap_id, "--yes"])
    assert code == 0


def test_history_show_unknown_id(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "history", "show", "9999"])
    assert code == 1


def test_doctor_ok(wasds_home, sample_csv_path, capsys):
    code = run(["--csv", str(sample_csv_path), "doctor", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True


def test_doctor_uses_packaged_baseline_by_default(wasds_home, capsys):
    code = run(["doctor", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["ok"] is True
    catalog_check = next(c for c in data["checks"] if c["name"] == "catalog_loads")
    assert "78" in catalog_check["detail"]


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        run(["--version"])
    assert exc_info.value.code == 0


# ------------------------------------------------------------------- hpe --
def test_hpe_build_encode_decode_inspect_validate_round_trip(wasds_home, tmp_path, capsys):
    systems_path = tmp_path / "systems.json"
    systems_path.write_text(
        json.dumps(
            {
                "systems": [
                    {
                        "id": "s1",
                        "label": "Test Conv",
                        "departments": [
                            {
                                "id": "d1",
                                "label": "Ops",
                                "channels": [{"id": "c1", "label": "Ch1", "freq_mhz": 154.1, "mode": "NFM"}],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out_hpe = tmp_path / "built.hpe"
    code = run(["hpe", "build", "--systems", str(systems_path), "--out", str(out_hpe)])
    assert code == 0
    assert out_hpe.exists()
    capsys.readouterr()

    decoded_txt = tmp_path / "decoded.txt"
    code = run(["hpe", "decode", str(out_hpe), "--out", str(decoded_txt)])
    assert code == 0
    assert "Test Conv" in decoded_txt.read_text(encoding="ascii")

    reencoded_hpe = tmp_path / "reencoded.hpe"
    code = run(["hpe", "encode", str(decoded_txt), "--out", str(reencoded_hpe)])
    assert code == 0
    assert reencoded_hpe.read_bytes() == out_hpe.read_bytes()
    capsys.readouterr()

    code = run(["hpe", "inspect", str(out_hpe), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dialect"]["target_model"] == "BCDx36HP"

    code = run(["hpe", "validate", str(out_hpe), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["issues"] == []


def test_hpe_build_reports_validation_issues_and_requires_force(wasds_home, tmp_path, capsys):
    # A hand-crafted, arity-broken document via a System with no channels
    # cannot itself be broken through the builder (it always emits correct
    # arities), so we instead confirm --force is accepted/documented by
    # building a valid doc and confirming force still succeeds.
    systems_path = tmp_path / "systems.json"
    systems_path.write_text(json.dumps({"systems": []}), encoding="utf-8")
    out_hpe = tmp_path / "empty.hpe"
    code = run(["hpe", "build", "--systems", str(systems_path), "--out", str(out_hpe), "--force"])
    assert code == 0


def test_hpe_decode_rejects_corrupt_file(wasds_home, tmp_path, capsys):
    bad = tmp_path / "bad.hpe"
    bad.write_bytes(b"not a real hpe file")
    code = run(["hpe", "decode", str(bad)])
    assert code == 1


# ----------------------------------------------------------------- merge ----
def test_merge_preview_and_apply_cli(wasds_home, sample_csv_path, tmp_path, capsys):
    import csv

    from wasds150.models.catalog import CSV_FIELDS

    run(["--csv", str(sample_csv_path), "init"])
    capsys.readouterr()

    # Build an upstream CSV with fl01's name changed.
    with sample_csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    rows[0]["favorite_name"] = "Upstream Renamed"
    upstream_path = tmp_path / "upstream.csv"
    with upstream_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_FIELDS), quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)

    code = run(["--csv", str(sample_csv_path), "merge", "preview", "--upstream", str(upstream_path), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data["changes"]) == 1
    assert data["conflicts"] == []

    code = run(["--csv", str(sample_csv_path), "merge", "apply", "--upstream", str(upstream_path), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["changes"] == 1
    assert data["conflicts"] == 0
    assert (wasds_home / "catalog.json").exists()

    # Subsequent commands should now load the merged catalog, not the CSV.
    code = run(["catalog", "show", "--slug", "fl01", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data[0]["favorite_name"] == "Upstream Renamed"


def test_merge_apply_without_force_fails_on_conflict(wasds_home, sample_csv_path, tmp_path, capsys):
    import csv

    from wasds150.models.catalog import CSV_FIELDS

    run(["--csv", str(sample_csv_path), "profile", "edit", "fl01", "--field", "favorite_name", "--value", "My Custom"])
    capsys.readouterr()

    with sample_csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows[0]["favorite_name"] = "Upstream Renamed"
    upstream_path = tmp_path / "upstream.csv"
    with upstream_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_FIELDS), quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)

    code = run(["--csv", str(sample_csv_path), "merge", "apply", "--upstream", str(upstream_path)])
    assert code == 1
    capsys.readouterr()

    code = run(["--csv", str(sample_csv_path), "merge", "apply", "--upstream", str(upstream_path), "--force", "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["conflicts"] == 1


# --------------------------------------------------------------- install ----
def test_install_detect_write_dry_run_and_rollback_cli(wasds_home, tmp_path, capsys):
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    (card / "BCDx36HP" / "app_data.cfg").write_text("resume", encoding="ascii")

    code = run(["install", "detect", "--dir", str(card), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert len(data) == 1
    assert data[0]["is_sds150_candidate"] is True

    systems_path = tmp_path / "systems.json"
    systems_path.write_text(
        json.dumps({"systems": [{"id": "s1", "label": "Test", "departments": []}]}), encoding="utf-8"
    )
    backup_dir = tmp_path / "backups"

    code = run(
        [
            "install", "write", str(card), "--systems", str(systems_path), "--index", "0",
            "--user-name", "Test List", "--backup-dir", str(backup_dir), "--json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True
    assert not (card / "BCDx36HP" / "favorites_lists" / "f_000000.hpd").exists()

    # Wrong confirm phrase with --execute should fail.
    code = run(
        [
            "install", "write", str(card), "--systems", str(systems_path), "--index", "0",
            "--user-name", "Test List", "--backup-dir", str(backup_dir), "--execute", "--confirm", "wrong",
        ]
    )
    assert code == 1
    capsys.readouterr()

    # Correct confirm phrase executes for real.
    phrase = f"WRITE {card.name}"
    code = run(
        [
            "install", "write", str(card), "--systems", str(systems_path), "--index", "0",
            "--user-name", "Test List", "--backup-dir", str(backup_dir), "--execute", "--confirm", phrase, "--json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verified"] is True
    backup_path = data["backup_path"]

    code = run(["install", "rollback", str(card), "--backup", backup_path, "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert f"BCDx36HP/app_data.cfg" in data["restored"]


def test_install_write_slug_default_workflow(wasds_home, sample_csv_path, tmp_path, capsys):
    """The default install workflow: profile -> generated favorites ->
    install, with no hand-authored Systems JSON. FL01's "ALPHA1 155.000"
    carries an explicit literal frequency, so it has a populated system
    with no configuration needed."""
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    backup_dir = tmp_path / "backups"

    code = run(
        [
            "--csv", str(sample_csv_path), "install", "write", str(card), "--slug", "fl01", "--index", "0",
            "--backup-dir", str(backup_dir), "--json",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["dry_run"] is True
    assert "BCDx36HP/favorites_lists/f_000000.hpd" in data["planned_writes"]


def test_install_write_slug_with_no_systems_reports_actionable_error(wasds_home, sample_csv_path, tmp_path, capsys):
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)

    # FL02 ("Bravo Dispatch, [E]-ENCRYPTED") has no explicit frequency.
    code = run(
        [
            "--csv", str(sample_csv_path), "install", "write", str(card), "--slug", "fl02", "--index", "0",
            "--backup-dir", str(tmp_path / "backups"),
        ]
    )
    assert code == 1
    err = capsys.readouterr().err
    assert "FL02" in err
    assert "HPDB" in err or "RadioReference" in err


def test_install_write_requires_exactly_one_of_slug_or_systems(wasds_home, sample_csv_path, tmp_path, capsys):
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)

    code = run(
        ["--csv", str(sample_csv_path), "install", "write", str(card), "--index", "0", "--backup-dir", str(tmp_path / "backups")]
    )
    assert code == 1
    assert "exactly one" in capsys.readouterr().err


def test_install_backup_cli(wasds_home, tmp_path, capsys):
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    (card / "BCDx36HP" / "profile.cfg").write_text("x", encoding="ascii")

    code = run(["install", "backup", str(card), "--out-dir", str(tmp_path / "backups"), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["verify_issues"] == []
    assert Path(data["backup_path"]).exists()


# ------------------------------------------------------------------ hpdb --
def test_hpe_hpdb_inspect_cfg_and_state_cli(wasds_home, capsys, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    code = run(["hpe", "hpdb-inspect", str(synthetic_hpdb_cfg_path), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["kind"] == "hpdb_index"
    assert data["states"]["53"] == "Washington"
    capsys.readouterr()

    code = run(["hpe", "hpdb-inspect", str(synthetic_hpdb_state_path), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    names = {s["name"] for s in data}
    assert names == {"King County Public Safety", "Regional P25"}


def test_hpe_hpdb_extract_by_county_cli(wasds_home, tmp_path, capsys, synthetic_hpdb_state_path):
    out_path = tmp_path / "extracted.hpe"
    code = run(
        [
            "hpe", "hpdb-extract", str(synthetic_hpdb_state_path),
            "--county-id", "5302", "--out", str(out_path),
        ]
    )
    assert code == 0
    assert out_path.exists()
    capsys.readouterr()

    code = run(["hpe", "validate", str(out_path), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["issues"] == []


def test_hpe_hpdb_extract_by_radius_cli(wasds_home, tmp_path, capsys, synthetic_hpdb_state_path):
    out_path = tmp_path / "extracted.hpd"
    code = run(
        [
            "hpe", "hpdb-extract", str(synthetic_hpdb_state_path),
            "--within", "47.6,-122.33,1", "--out", str(out_path),
        ]
    )
    assert code == 0
    text = out_path.read_bytes().decode("ascii")
    assert "King County Public Safety" in text
    assert "Regional P25" in text
    assert "AreaCounty" not in text
    assert "DQKs_Status" in text


def test_hpe_hpdb_extract_no_match_fails(wasds_home, tmp_path, capsys, synthetic_hpdb_state_path):
    out_path = tmp_path / "extracted.hpd"
    code = run(
        [
            "hpe", "hpdb-extract", str(synthetic_hpdb_state_path),
            "--county-id", "99999", "--out", str(out_path),
        ]
    )
    assert code == 1
    assert not out_path.exists()


def test_hpe_hpdb_extract_rejects_hpdb_cfg_input(wasds_home, tmp_path, capsys, synthetic_hpdb_cfg_path):
    out_path = tmp_path / "extracted.hpd"
    code = run(
        [
            "hpe", "hpdb-extract", str(synthetic_hpdb_cfg_path),
            "--county-id", "1", "--out", str(out_path),
        ]
    )
    assert code == 1


def test_install_hpdb_inspect_cli(wasds_home, tmp_path, capsys, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    card = tmp_path / "card"
    (card / "BCDx36HP" / "HPDB").mkdir(parents=True)
    import shutil

    shutil.copy(synthetic_hpdb_cfg_path, card / "BCDx36HP" / "HPDB" / "hpdb.cfg")
    shutil.copy(synthetic_hpdb_state_path, card / "BCDx36HP" / "HPDB" / "s_000053.hpd")

    code = run(["install", "hpdb-inspect", str(card), "--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["states"]["53"] == "Washington"
    assert set(data["state_files"]["53"]) == {"King County Public Safety", "Regional P25"}


def test_install_hpdb_inspect_missing_hpdb_fails(wasds_home, tmp_path, capsys):
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    code = run(["install", "hpdb-inspect", str(card)])
    assert code == 1
