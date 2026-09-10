"""Fleet model, registry, settings, sync state and generated docs."""
from __future__ import annotations

import pytest

from conftest import REPO_ROOT
from wasds150.export.registry import get_target
from wasds150.fleet.describe import render_markdown, stale_docs, sync_text
from wasds150.fleet.model import (
    LOAD_AUTOMATED,
    LOAD_GUIDED,
    STEP_AUTO,
    FleetRadio,
    InputSpec,
    StepSpec,
    render_instructions,
)
from wasds150.fleet.registry import FLEET, get_fleet_radio
from wasds150.fleet.settings import FleetSettings, parse_assignment
from wasds150.fleet.state import FleetState, RadioSyncRecord, radio_status, sha256_of_path
from wasds150.plans import get_plan
from wasds150.radios.registry import get_profile


# --------------------------------------------------------------- registry --
def test_every_fleet_radio_is_a_registered_radio_with_a_usable_target():
    assert list(FLEET) == ["sds150", "td-h9", "th-d75", "ftx1", "at-d890uv"]
    for radio in FLEET.values():
        get_profile(radio.radio_id)
        if radio.plan_id:
            assert get_plan(radio.plan_id).radio_id == radio.radio_id
            assert get_target(radio.target_id).radio_id == radio.radio_id


def test_load_paths_follow_the_decisions():
    automated = {r.radio_id for r in FLEET.values() if r.load_path == LOAD_AUTOMATED}
    assert automated == {"sds150", "td-h9"}
    for radio in FLEET.values():
        if radio.load_path == LOAD_GUIDED:
            assert radio.vendor_app is not None, radio.radio_id
            assert any(step.kind != STEP_AUTO for step in radio.steps)


def test_unknown_radio_is_a_key_error():
    with pytest.raises(KeyError):
        get_fleet_radio("ic-705")


def test_duplicate_step_ids_are_rejected():
    step = StepSpec("a", "A", "do it")
    with pytest.raises(ValueError):
        FleetRadio("x", "", "", LOAD_GUIDED, steps=(step, step))


def test_input_and_step_kinds_are_validated():
    with pytest.raises(ValueError):
        InputSpec("port", "serial", "Port")
    with pytest.raises(ValueError):
        StepSpec("a", "A", "do it", kind="later")


def test_placeholders_fill_known_values_and_mark_unknown_ones():
    assert render_instructions("Open {export} for {radio}", {"export": "x.csv"}) == "Open x.csv for <radio>"


# ------------------------------------------------------------------- docs --
def test_markdown_numbers_the_steps_and_fills_the_plan_id():
    text = render_markdown(get_fleet_radio("at-d890uv"))
    assert "1. **Export the CPS bundle** _(automatic)_ - Export at-d890uv-fleet" in text
    assert "`at-d890uv.cps_app`" in text
    assert "WA7DAM" in text


def test_sync_replaces_only_the_generated_section():
    radio = get_fleet_radio("td-h9")
    doc = "Intro\n\n<!-- fleet:begin td-h9 -->\nold\n<!-- fleet:end td-h9 -->\n\nOutro\n"
    updated = sync_text(doc, radio)
    assert updated.startswith("Intro\n\n<!-- fleet:begin td-h9 -->\n### TIDRADIO TD-H9")
    assert updated.endswith("<!-- fleet:end td-h9 -->\n\nOutro\n")
    assert sync_text(updated, radio) == updated


def test_committed_fleet_doc_matches_the_registry():
    assert stale_docs(REPO_ROOT) == [], "run 'wasds150 fleet docs' and commit docs/fleet-updates.md"


# --------------------------------------------------------------- settings --
def test_settings_store_clear_and_fall_back_to_defaults(tmp_path):
    radio = get_fleet_radio("td-h9")
    settings = FleetSettings()
    assert [spec.id for spec in settings.missing(radio)] == ["com_port"]
    settings.set("td-h9", "com_port", "COM7")
    assert settings.values_for(radio) == {"com_port": "COM7", "label": "td-h9"}
    assert settings.missing(radio) == []
    path = tmp_path / "fleet-settings.json"
    settings.save(path)
    assert FleetSettings.load(path).get("td-h9", "com_port") == "COM7"
    settings.set("td-h9", "com_port", "")
    assert settings.radios == {}


def test_assignment_parsing():
    assert parse_assignment("TD-H9.com_port=COM7") == ("td-h9", "com_port", "COM7")
    assert parse_assignment("ftx1.copy_to=") == ("ftx1", "copy_to", "")
    for bad in ("td-h9=COM7", "com_port=COM7x", ".x=1", "td-h9.com_port"):
        with pytest.raises(ValueError):
            parse_assignment(bad)


# ------------------------------------------------------------------ state --
def _record(**overrides) -> RadioSyncRecord:
    values = dict(
        radio_id="td-h9",
        plan_id="td-h9-fleet",
        synced_at="2026-09-10T00:00:00+00:00",
        catalog_content_hash="c1",
        catalog_structure_hash="s1",
        plan_fingerprint="p1",
    )
    values.update(overrides)
    return RadioSyncRecord(**values)


def test_status_reasons():
    radio = get_fleet_radio("td-h9")
    fresh = radio_status(radio, _record(), content_hash="c1", structure="s1", current_plan_fingerprint="p1")
    assert not fresh.stale and fresh.reasons == []
    never = radio_status(radio, None, content_hash="c1", structure="s1")
    assert never.reasons == ["never synced"]
    moved = radio_status(radio, _record(), content_hash="c1", structure="s2", current_plan_fingerprint="p1")
    assert moved.stale and moved.reasons[0].startswith("channels or talkgroups changed")
    replanned = radio_status(radio, _record(plan_id="h9-ozette"), content_hash="c1", structure="s1")
    assert replanned.reasons == ["plan changed (h9-ozette -> td-h9-fleet)"]
    edited = radio_status(radio, _record(), content_hash="c1", structure="s1", current_plan_fingerprint="p2")
    assert edited.reasons == ["plan definition changed"]


def test_state_round_trips(tmp_path):
    state = FleetState()
    state.record(_record(verified=True))
    path = tmp_path / "fleet.json"
    state.save(path)
    loaded = FleetState.load(path)
    assert loaded.records["td-h9"].verified is True
    assert FleetState.load(tmp_path / "missing.json").records == {}


def test_directory_hash_is_stable_and_content_sensitive(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "a.csv").write_text("1", encoding="utf-8")
    (bundle / "b.csv").write_text("2", encoding="utf-8")
    first = sha256_of_path(bundle)
    assert sha256_of_path(bundle) == first
    (bundle / "b.csv").write_text("3", encoding="utf-8")
    assert sha256_of_path(bundle) != first
    assert len(sha256_of_path(bundle / "a.csv")) == 64
