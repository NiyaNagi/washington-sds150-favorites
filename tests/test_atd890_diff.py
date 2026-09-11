"""Comparing a generated CPS bundle with a read-back Export All."""
from __future__ import annotations

import csv
import importlib.util
import io
import shutil

import pytest

from conftest import REPO_CSV_PATH, REPO_ROOT
from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.export.atd890_diff import compare_bundle
from wasds150.plan.service import export_plan


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    config = AppConfig(home=tmp_path_factory.mktemp("home"))
    config.ensure_dirs()
    ctx = build_context(config, csv_override=REPO_CSV_PATH)
    return export_plan(ctx, "atd890-scan", target_id="atd890-cps", out_dir=tmp_path_factory.mktemp("out")).csv_path


@pytest.fixture()
def readback(bundle, tmp_path):
    target = tmp_path / "readback"
    shutil.copytree(bundle, target)
    return target


def _edit(path, change):
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="ascii"))))
    change(rows)
    buffer = io.StringIO()
    csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\r\n").writerows(rows)
    path.write_text(buffer.getvalue(), encoding="ascii")


def _column(rows, name):
    return rows[0].index(name)


def test_an_identical_read_back_is_clean(bundle, readback):
    diff = compare_bundle(bundle, readback)
    assert diff.clean
    assert diff.summary().startswith("clean")


def test_renumbering_and_reformatting_are_ignored(bundle, readback):
    def renumber(rows):
        rows[1][0] = "999"
        rx = _column(rows, "Receive Frequency")
        rows[1][rx] = rows[1][rx].rstrip("0")
    _edit(readback / "Channel.CSV", renumber)
    assert compare_bundle(bundle, readback).clean


def test_a_different_radio_id_is_a_real_difference(bundle, readback):
    _edit(readback / "RadioIDList.CSV", lambda rows: rows[1].__setitem__(1, "1"))
    diff = compare_bundle(bundle, readback)
    radio_ids = next(f for f in diff.files if f.name == "RadioIDList.CSV")
    assert not diff.clean and [c.column for c in radio_ids.cells] == ["Radio ID"]


def test_a_changed_cell_a_lost_row_and_member_order(bundle, readback):
    def change(rows):
        rows[1][_column(rows, "Transmit Power")] = "Low" if rows[1][_column(rows, "Transmit Power")] != "Low" else "Mid"
        del rows[2]
    _edit(readback / "Channel.CSV", change)

    def reorder(rows):
        # The first zone with several members: names, RX and TX lists in step.
        row = next(r for r in rows[1:] if "|" in r[2])
        for column in (2, 3, 4):
            row[column] = "|".join(reversed(row[column].split("|")))

    _edit(readback / "DMRZone.CSV", reorder)
    diff = compare_bundle(bundle, readback)
    assert not diff.clean
    channel = next(f for f in diff.files if f.name == "Channel.CSV")
    assert len(channel.missing_rows) == 1
    assert [c.column for c in channel.cells] == ["Transmit Power"]
    zone = next(f for f in diff.files if f.name == "DMRZone.CSV")
    assert zone.clean and any(c.order_only for c in zone.cells)
    ignored = compare_bundle(bundle, readback, ignore=[("Channel.CSV", "Transmit Power")])
    assert next(f for f in ignored.files if f.name == "Channel.CSV").cells == []


def test_a_missing_file_is_reported(bundle, readback):
    (readback / "FM.CSV").unlink()
    diff = compare_bundle(bundle, readback)
    assert next(f for f in diff.files if f.name == "FM.CSV").missing_file and not diff.clean


def _script():
    path = REPO_ROOT / "scripts" / "radios" / "diff_atd890_export.py"
    spec = importlib.util.spec_from_file_location("diff_atd890_export", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_script_exit_codes_and_hashes(bundle, readback, capsys):
    script = _script()
    assert script.main(["--bundle", str(bundle), "--readback", str(readback)]) == 0
    out = capsys.readouterr().out
    assert "clean" in out and "  Channel.CSV" in out and "  bundle" in out
    _edit(readback / "Channel.CSV", lambda rows: rows[1].__setitem__(_column(rows, "Channel Name"), "Renamed"))
    assert script.main(["--bundle", str(bundle), "--readback", str(readback), "--json"]) == 1
    assert script.main(["--bundle", str(bundle), "--readback", str(readback), "--ignore", "nocolon"]) == 2
