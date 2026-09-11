"""Optional Settings / hot key template: capture, replay, manifest."""
from __future__ import annotations

import csv
import io

import pytest

from conftest import REPO_CSV_PATH
from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.export.atd890_cps import render_files
from wasds150.export.atd890_settings import Atd890Settings, render_settings_files
from wasds150.export.atd890_settings_template import SettingsTemplate, diff_export_all, load_packaged_template
from wasds150.plan.service import resolve_named_plan

HEADER = '"No.","Digital Monitor","Mem Zone A","Priority Zone A","Power-on Display Char","TOT"\r\n'
FRESH = HEADER + '"1","Off","Zone 1","None","","60"\r\n'
CONFIGURED = HEADER + '"1","Double Slot","Ham 2m","Ham 2m","KA7XYZ","180"\r\n'
HOTKEY = '"No.","Mode","Menu"\r\n"1","Call","None"\r\n'


def _export_all(folder, optional):
    folder.mkdir(parents=True)
    (folder / "OptionalSetting.CSV").write_text(optional, encoding="utf-8")
    (folder / "HotKey_QuickCall.CSV").write_text(HOTKEY, encoding="utf-8")
    (folder / "Channel.CSV").write_text('"No.","Channel Name"\r\n', encoding="utf-8")
    return folder


@pytest.fixture()
def template(tmp_path):
    return diff_export_all(_export_all(tmp_path / "fresh", FRESH), _export_all(tmp_path / "configured", CONFIGURED))


def _rows(text):
    return list(csv.reader(io.StringIO(text)))


def test_the_diff_keeps_settings_and_blanks_identity(template):
    assert [f.name for f in template.files] == ["HotKey_QuickCall.CSV", "OptionalSetting.CSV"]
    optional = template.files[1]
    changed = {optional.header[c]: (before, after) for _r, c, before, after in optional.changed}
    assert changed == {
        "Digital Monitor": ("Off", "Double Slot"), "Mem Zone A": ("Zone 1", "Ham 2m"),
        "Priority Zone A": ("None", "Ham 2m"), "TOT": ("60", "180"),
    }
    assert optional.identity == [[0, 4, "callsign"]]
    assert "KA7XYZ" not in str(template.to_dict())
    assert template.files[0].changed == []


def test_the_template_round_trips_through_json(template, tmp_path):
    path = tmp_path / "template.json"
    template.save(path)
    assert SettingsTemplate.load(path).to_dict() == template.to_dict()
    assert load_packaged_template(path).files[1].name == "OptionalSetting.CSV"
    assert load_packaged_template(tmp_path / "absent.json") is None


def test_replay_fills_identity_and_checks_zone_names(template):
    files, warnings = render_settings_files(template, zone_names=["Ham 2m", "Ham 70cm"],
                                            settings=Atd890Settings(callsign="KA7XYZ", overrides={"TOT": "120"}))
    row = _rows(files["OptionalSetting.CSV"])[1]
    assert row == ["1", "Double Slot", "Ham 2m", "Ham 2m", "KA7XYZ", "120"]
    assert warnings == []
    files, warnings = render_settings_files(template, zone_names=["DMR Core"])
    row = _rows(files["OptionalSetting.CSV"])[1]
    assert row[2] == row[3] == "DMR Core" and row[4] == "WA7DAM"
    assert len(warnings) == 2 and "does not have" in warnings[0]


def test_no_settings_files_is_an_error(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError):
        diff_export_all(empty, empty)


def test_settings_files_join_the_bundle_and_manifest_only_with_a_template(template, tmp_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    ctx = build_context(config, csv_override=REPO_CSV_PATH)
    _plan, resolved = resolve_named_plan(ctx, "atd890-scan")
    plain, _ = render_files(resolved)
    assert "OptionalSetting.CSV" not in plain
    assert plain["atd890-scan.LST"].splitlines()[0] == "9"
    with_settings, _ = render_files(resolved, settings_template=template)
    manifest = with_settings["atd890-scan.LST"].splitlines()
    assert manifest[0] == "11" and manifest[-1] == '10,"OptionalSetting.CSV"'
    assert _rows(with_settings["OptionalSetting.CSV"])[1][2] == "Ham 2m"
