"""Tests for the shared plan service layer.

These exercise the code path that both the CLI and the web UI call, so a
regression here would break both front ends at once.
"""
from __future__ import annotations

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.plan.service import (
    DEFAULT_OUT_DIR,
    channel_row,
    export_plan,
    plan_detail,
    plan_index,
    resolve_named_plan,
)


@pytest.fixture()
def real_ctx(tmp_path, repo_csv_path):
    """A context built from the real catalog, which contains the OZ01 rows
    the shipped TD-H9 plan selects from."""
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=repo_csv_path)


def test_plan_index_lists_registered_plans():
    rows = plan_index()
    assert rows, "expected at least one registered plan"
    ids = {row["id"] for row in rows}
    assert "h9-ozette" in ids
    for row in rows:
        assert row["blocks"] > 0
        assert row["radio_id"]


def test_resolve_named_plan_returns_channels(real_ctx):
    plan, resolved = resolve_named_plan(real_ctx, "h9-ozette")
    assert plan.id == "h9-ozette"
    assert resolved.profile.id == "td-h9"
    assert resolved.slots_used > 100
    # The plan must never overrun the radio.
    assert resolved.capacity is not None
    assert resolved.slots_used <= resolved.capacity


def test_resolve_unknown_plan_raises(real_ctx):
    with pytest.raises(KeyError):
        resolve_named_plan(real_ctx, "no-such-plan")


def test_plan_detail_is_json_safe(real_ctx):
    import json

    _plan, resolved = resolve_named_plan(real_ctx, "h9-ozette")
    detail = plan_detail(resolved)
    # Must survive a round trip through the JSON encoder the API uses.
    encoded = json.dumps(detail)
    assert json.loads(encoded)["slots_used"] == resolved.slots_used
    assert detail["radio"]["id"] == "td-h9"
    assert detail["channels"], "expected resolved channels in the detail payload"


def test_channel_row_exposes_programming_fields(real_ctx):
    _plan, resolved = resolve_named_plan(real_ctx, "h9-ozette")
    row = channel_row(resolved.channels[0])
    for key in ("slot", "name", "rx_mhz", "transmit", "mode", "power", "block"):
        assert key in row


def test_export_plan_writes_csv_and_report(real_ctx, tmp_path):
    out = tmp_path / "radios"
    export = export_plan(real_ctx, "h9-ozette", target_id="chirp-csv", out_dir=out)

    assert export.csv_path.is_file()
    assert export.report_path.is_file()
    assert export.rows > 100

    text = export.csv_path.read_text(encoding="utf-8")
    assert text.startswith("Location,Name,Frequency")
    # One header line plus one line per programmed channel.
    assert len(text.strip().splitlines()) == export.rows + 1


def test_export_plan_rejects_unimplemented_target(real_ctx, tmp_path):
    with pytest.raises((NotImplementedError, ValueError, KeyError)):
        export_plan(real_ctx, "h9-ozette", target_id="rtsystems-csv", out_dir=tmp_path)


def test_export_plan_rejects_unknown_target(real_ctx, tmp_path):
    with pytest.raises(KeyError):
        export_plan(real_ctx, "h9-ozette", target_id="not-a-target", out_dir=tmp_path)


def test_export_to_dict_is_serializable(real_ctx, tmp_path):
    import json

    export = export_plan(real_ctx, "h9-ozette", out_dir=tmp_path)
    payload = json.loads(json.dumps(export.to_dict()))
    assert payload["plan"] == "h9-ozette"
    assert payload["target"] == "chirp-csv"
    assert len(payload["files"]) == 2


def test_default_out_dir_matches_cli_default():
    # The CLI advertises this path in --help; the UI builds the flash command
    # from it. If they diverge the Flash button points at a stale file.
    assert DEFAULT_OUT_DIR == "wasds150-output/radios"


def test_export_can_copy_to_a_second_directory(real_ctx, tmp_path):
    """Exports land in the repo, but radios are programmed from elsewhere.

    A stale working copy opens cleanly in the vendor programmer with the right
    channel count and frequencies, so the drift is invisible until something
    behaves oddly on the air. Copying in the same step removes the gap.
    """
    out = tmp_path / "repo"
    working = tmp_path / "programming-folder"
    export = export_plan(real_ctx, "h9-ozette", out_dir=out, copy_to=working)

    assert export.copies, "expected the programming file to be copied"
    copied = working / export.csv_path.name
    assert copied.is_file()
    assert copied.read_bytes() == export.csv_path.read_bytes()
    assert (working / export.report_path.name).is_file()


def test_export_copy_to_same_directory_is_a_no_op(real_ctx, tmp_path):
    """Copying a file onto itself must not truncate it."""
    out = tmp_path / "radios"
    export = export_plan(real_ctx, "h9-ozette", out_dir=out, copy_to=out)
    assert export.copies == []
    assert export.csv_path.stat().st_size > 0
