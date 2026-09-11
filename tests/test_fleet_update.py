"""The fleet update wizard, driven end to end with fake hardware."""
from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import pytest

from conftest import REPO_CSV_PATH
from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.fleet.service import fleet_status
from wasds150.fleet.update import (
    FleetUpdateSpec,
    UpdateHooks,
    resume_fleet_update,
    selected_sources,
    start_fleet_update,
)
from wasds150.jobs.runner import JobRunner
from wasds150.radios.programmer import ProgrammerRun
from wasds150.update.pipeline import SourceRunOutcome, UpdateRunResult


@pytest.fixture()
def ctx(tmp_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    return build_context(config, csv_override=REPO_CSV_PATH)


@pytest.fixture()
def runner(ctx):
    runner = JobRunner(ctx.config.jobs_dir)
    runner.POLL_SECONDS = 0.02
    return runner


def _never(*args, **kwargs):
    raise AssertionError("this hook must not be called")


def _hooks(**overrides) -> UpdateHooks:
    values = dict(fetch=_never, launch=_never, program_tdh9=_never, install_sentinel=_never)
    values.update(overrides)
    return UpdateHooks(**values)


def _drive(runner, job_id, answers=None, timeout=120):
    """Answer every waiting step (by the last part of its id) until the job stops."""
    answers = answers or {}
    deadline = time.monotonic() + timeout
    answered = set()
    while time.monotonic() < deadline:
        status = runner.get(job_id)
        if not status.active:
            return status
        waiting = status.waiting or {}
        step_id = waiting.get("step_id")
        if status.status == "waiting" and step_id and (step_id, status.last_seq) not in answered:
            decision, inputs = answers.get(step_id.rsplit(".", 1)[-1], ("done", {}))
            runner.answer(job_id, step_id, decision, inputs)
            answered.add((step_id, status.last_seq))
        time.sleep(0.02)
    raise AssertionError("the job did not finish in time")


def _steps(status):
    return {step.id: step for step in status.steps}


def _programmer(calls, fail_on_execute=False):
    def program(*, port, csv_path, label, execute, on_line, should_cancel):
        calls.append((port, execute))
        on_line("staged" if not execute else "written")
        ok = not (execute and fail_on_execute)
        return ProgrammerRun(ok=ok, command=[], returncode=0 if ok else 2, stdout="", stderr="" if ok else "boom")

    return program


# -------------------------------------------------------------- dry runs --
def test_a_dry_run_exports_and_touches_nothing(ctx, runner, tmp_path):
    spec = FleetUpdateSpec(radio_ids=["td-h9", "at-d890uv"], refresh_sources=False, out_dir=str(tmp_path / "out"))
    job_id = start_fleet_update(runner, ctx, spec, hooks=_hooks())
    status = _drive(runner, job_id)
    assert status.status == "finished", status.error
    steps = _steps(status)
    assert steps["radio.td-h9.export"].status == "finished"
    assert (tmp_path / "out" / "td-h9-fleet.csv").is_file()
    assert (tmp_path / "out" / "at-d890uv-fleet").is_dir()
    for step_id in ("radio.td-h9.flash", "radio.at-d890uv.write-radio", "radio.td-h9.record"):
        assert steps[step_id].status == "skipped", step_id
    assert all(s.stale for s in fleet_status(ctx))


def test_a_dry_run_plans_the_scanner_install(ctx, runner, tmp_path):
    calls = []

    def install(workspace, profile_name, favorites, **kwargs):
        calls.append(kwargs["execute"])
        return SimpleNamespace(assignments=list(favorites)[:3], warnings=["one warning"], plan_id="p1")

    spec = FleetUpdateSpec(
        radio_ids=["sds150"], refresh_sources=False, out_dir=str(tmp_path / "out"),
        inputs={"sds150": {"sentinel_profile": "Test", "sentinel_workspace": str(tmp_path / "ws")}},
    )
    status = _drive(runner, start_fleet_update(runner, ctx, spec, hooks=_hooks(install_sentinel=install)))
    assert status.status == "finished", status.error
    install_step = _steps(status)["radio.sds150.install"]
    assert install_step.status == "finished"
    assert install_step.message.startswith("dry run: 3 list(s)")
    assert calls == [False]
    assert (tmp_path / "out" / "sds150" / "hpe").is_dir()


# --------------------------------------------------------------- execute --
def test_execute_programs_the_td_h9_and_records_the_sync(ctx, runner, tmp_path):
    calls = []
    spec = FleetUpdateSpec(
        radio_ids=["td-h9"], refresh_sources=False, execute=True, out_dir=str(tmp_path / "out"),
        inputs={"td-h9": {"com_port": "COM7"}},
    )
    job_id = start_fleet_update(runner, ctx, spec, hooks=_hooks(program_tdh9=_programmer(calls)))
    status = _drive(runner, job_id, {"flash": ("done", {"confirm": "WRITE COM7"})})
    assert status.status == "finished", status.error
    assert calls == [("COM7", False), ("COM7", True)]
    steps = _steps(status)
    assert steps["radio.td-h9.record"].status == "finished"
    assert steps["radio.td-h9.verify"].message == "verified"
    by_radio = {s.radio_id: s for s in fleet_status(ctx)}
    assert not by_radio["td-h9"].stale
    assert by_radio["td-h9"].record.verified is True
    events = [e.kind for e in runner.events(job_id)]
    assert "radio.diff" in events and "step.log" in events


def test_a_wrong_confirmation_writes_nothing(ctx, runner, tmp_path):
    calls = []
    spec = FleetUpdateSpec(
        radio_ids=["td-h9"], refresh_sources=False, execute=True, out_dir=str(tmp_path / "out"),
        inputs={"td-h9": {"com_port": "COM7"}},
    )
    job_id = start_fleet_update(runner, ctx, spec, hooks=_hooks(program_tdh9=_programmer(calls)))
    status = _drive(runner, job_id, {"flash": ("done", {"confirm": "WRITE COM8"})})
    assert status.status == "finished"
    assert calls == [("COM7", False)]
    steps = _steps(status)
    assert steps["radio.td-h9.flash"].status == "skipped"
    assert steps["radio.td-h9.record"].status == "skipped"


def test_a_guided_radio_walks_its_checklist(ctx, runner, tmp_path):
    launched = []
    spec = FleetUpdateSpec(
        radio_ids=["at-d890uv"], refresh_sources=False, execute=True, out_dir=str(tmp_path / "out"),
        inputs={"at-d890uv": {"cps_app": sys.executable}},
    )
    hooks = _hooks(launch=lambda exe, args: launched.append((str(exe), args)))
    job_id = start_fleet_update(runner, ctx, spec, hooks=hooks)
    status = _drive(runner, job_id, {"export-all-readback": ("skip", {})})
    assert status.status == "finished", status.error
    assert launched == [(sys.executable, [])]
    steps = _steps(status)
    assert steps["radio.at-d890uv.import-all"].status == "finished"
    assert steps["radio.at-d890uv.export-all-readback"].status == "skipped"
    assert steps["radio.at-d890uv.record"].status == "finished"
    record = {s.radio_id: s for s in fleet_status(ctx)}["at-d890uv"].record
    assert record is not None and record.export_sha256


def test_skip_manual_leaves_the_radio_unrecorded(ctx, runner, tmp_path):
    spec = FleetUpdateSpec(
        radio_ids=["ftx1"], refresh_sources=False, execute=True, skip_manual=True, launch_apps=False,
        out_dir=str(tmp_path / "out"),
    )
    status = _drive(runner, start_fleet_update(runner, ctx, spec, hooks=_hooks()), {"confirm-count": ("skip", {})})
    assert status.status == "finished"
    steps = _steps(status)
    assert steps["radio.ftx1.send-to-radio"].status == "skipped"
    assert steps["radio.ftx1.record"].status == "skipped"


def test_resume_reuses_the_export_after_a_failed_write(ctx, runner, tmp_path):
    spec = FleetUpdateSpec(
        radio_ids=["td-h9"], refresh_sources=False, execute=True, out_dir=str(tmp_path / "out"),
        inputs={"td-h9": {"com_port": "COM7"}},
    )
    answers = {"flash": ("done", {"confirm": "WRITE COM7"})}
    failing = _hooks(program_tdh9=_programmer([], fail_on_execute=True))
    first = _drive(runner, start_fleet_update(runner, ctx, spec, hooks=failing), answers)
    assert first.status == "failed" and "td-h9" in first.error

    calls = []
    second_id = resume_fleet_update(runner, ctx, first.job_id, hooks=_hooks(program_tdh9=_programmer(calls)))
    second = _drive(runner, second_id, answers)
    assert second.status == "finished", second.error
    assert second.resumed_from == first.job_id
    export = _steps(second)["radio.td-h9.export"]
    assert export.status == "skipped" and "reused" in export.message
    assert calls[-1] == ("COM7", True)


# ---------------------------------------------------------------- sources --
def test_sources_that_fail_do_not_stop_the_update(ctx, runner, tmp_path):
    def fetch(context, names):
        return UpdateRunResult(outcomes=[SourceRunOutcome(source_id=names[0], ok=False, error="offline")])

    spec = FleetUpdateSpec(radio_ids=["td-h9"], only_sources=["noaa_nwr"], out_dir=str(tmp_path / "out"))
    status = _drive(runner, start_fleet_update(runner, ctx, spec, hooks=_hooks(fetch=fetch)))
    assert status.status == "finished"
    steps = _steps(status)
    assert steps["sources.noaa_nwr"].status == "failed"
    assert steps["sources.wwara"].status == "skipped" and steps["sources.wwara"].message == "not selected"
    assert steps["sources.merge"].message == "no new facts"
    assert status.result["sources"]["noaa_nwr"].startswith("failed")


def test_a_source_with_nothing_new_leaves_the_catalog_alone(ctx, runner, tmp_path):
    def fetch(context, names):
        return UpdateRunResult(outcomes=[SourceRunOutcome(source_id=names[0], ok=True)])

    spec = FleetUpdateSpec(radio_ids=["td-h9"], only_sources=["amsat"], out_dir=str(tmp_path / "out"))
    status = _drive(runner, start_fleet_update(runner, ctx, spec, hooks=_hooks(fetch=fetch)))
    steps = _steps(status)
    assert steps["sources.amsat"].status == "finished"
    assert steps["sources.merge"].status == "skipped"
    assert not list(ctx.config.updates_dir.glob("*.json"))


def test_source_selection_prefers_stale_sources_and_respects_skips(ctx):
    stale = selected_sources(ctx, FleetUpdateSpec(radio_ids=["td-h9"]))
    assert "noaa_nwr" in stale and "sentinel_local" not in stale  # nothing cached yet; Sentinel unconfigured
    assert "noaa_nwr" not in selected_sources(ctx, FleetUpdateSpec(radio_ids=["td-h9"], skip_sources=["noaa_nwr"]))
    assert selected_sources(ctx, FleetUpdateSpec(radio_ids=["td-h9"], only_sources=["amsat"])) == ["amsat"]
    assert selected_sources(ctx, FleetUpdateSpec(radio_ids=["td-h9"], refresh_sources=False)) == []


# ------------------------------------------------------------------- spec --
def test_spec_round_trips_and_validates():
    spec = FleetUpdateSpec(radio_ids=["TD-H9", "td-h9", "ftx1"], execute=True)
    assert FleetUpdateSpec.from_dict({**spec.to_dict(), "unknown": 1}).to_dict() == spec.to_dict()
    assert spec.validate().radio_ids == ["td-h9", "ftx1"]
    with pytest.raises(ValueError):
        FleetUpdateSpec().validate()
    with pytest.raises(KeyError):
        FleetUpdateSpec(radio_ids=["ic-705"]).validate()
