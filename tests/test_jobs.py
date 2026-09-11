"""The background job runner: steps, events, operator answers, restarts."""
from __future__ import annotations

import time

import pytest

from wasds150.jobs.context import StepSkipped
from wasds150.jobs.runner import JobBusy, JobRunner


def _runner(tmp_path) -> JobRunner:
    runner = JobRunner(tmp_path / "jobs")
    runner.POLL_SECONDS = 0.02
    return runner


def _until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition not reached in time")


def _waiting_on(runner, job_id):
    status = runner.get(job_id)
    return (status.waiting or {}).get("step_id") if status.status == "waiting" else None


def test_a_finished_job_keeps_its_steps_events_and_result(tmp_path):
    runner = _runner(tmp_path)

    def work(job):
        with job.step("a", "Step A") as handle:
            job.log("hello")
            handle.message = "ok"
        job.skip("b", "Step B", "not needed")
        with job.step("c", "Step C"):
            raise StepSkipped("nothing to do")
        return {"answer": 42}

    job_id = runner.submit("test", "Test job", work)
    status = runner.wait(job_id, 5)
    assert status.status == "finished" and status.result == {"answer": 42}
    assert [(s.id, s.status) for s in status.steps] == [("a", "finished"), ("b", "skipped"), ("c", "skipped")]
    kinds = [event.kind for event in runner.events(job_id)]
    assert kinds[0] == "job.started" and kinds[-1] == "job.finished"
    assert "step.log" in kinds

    reopened = JobRunner(tmp_path / "jobs")
    assert reopened.get(job_id).status == "finished"
    later = reopened.events(job_id, since_seq=2)
    assert later and later[0].seq == 3


def test_a_failing_step_fails_the_job(tmp_path):
    runner = _runner(tmp_path)

    def work(job):
        with job.step("a", "Step A"):
            raise ValueError("boom")

    status = runner.wait(runner.submit("test", "Failing", work), 5)
    assert status.status == "failed" and "boom" in status.error
    assert status.steps[0].status == "failed"


def test_the_operator_answers_a_checklist_step_and_an_input(tmp_path):
    runner = _runner(tmp_path)

    def work(job):
        with job.step("press", "Press the button") as handle:
            handle.message = job.wait_for_user("Press it").decision
        with job.step("port", "Choose the port"):
            port = job.require_input({"id": "com_port", "label": "Port", "kind": "com_port"})
        return {"port": port}

    job_id = runner.submit("test", "Interactive", work)
    _until(lambda: _waiting_on(runner, job_id) == "press")
    with pytest.raises(ValueError):
        runner.answer(job_id, "port", "done")
    runner.answer(job_id, "press", "done")
    _until(lambda: _waiting_on(runner, job_id) == "port")
    assert runner.get(job_id).waiting["inputs"][0]["id"] == "com_port"
    runner.answer(job_id, "port", "done", {"com_port": "COM7"})
    status = runner.wait(job_id, 5)
    assert status.result == {"port": "COM7"}
    assert status.steps[0].message == "done"


def test_abort_cancels_the_job(tmp_path):
    runner = _runner(tmp_path)

    def work(job):
        with job.step("w", "Wait"):
            job.wait_for_user("anything")

    job_id = runner.submit("test", "Abortable", work)
    _until(lambda: _waiting_on(runner, job_id) == "w")
    runner.answer(job_id, "w", "abort")
    status = runner.wait(job_id, 5)
    assert status.status == "cancelled"
    assert status.steps[0].status == "failed"


def test_cancel_stops_a_running_job(tmp_path):
    runner = _runner(tmp_path)

    def work(job):
        with job.step("loop", "Loop"):
            while True:
                job.check_cancelled()
                time.sleep(0.01)

    job_id = runner.submit("test", "Loop", work)
    _until(lambda: runner.get(job_id).status == "running")
    assert runner.cancel(job_id) is True
    assert runner.wait(job_id, 5).status == "cancelled"
    assert runner.cancel(job_id) is False


def test_only_one_job_per_exclusive_group(tmp_path):
    runner = _runner(tmp_path)

    def waits(job):
        with job.step("w", "Wait"):
            job.wait_for_user("hold")

    first = runner.submit("test", "First", waits)
    _until(lambda: _waiting_on(runner, first) == "w")
    with pytest.raises(JobBusy) as busy:
        runner.submit("test", "Second", waits)
    assert busy.value.job_id == first
    other = runner.submit("test", "Other group", lambda job: {}, exclusive="other")
    assert runner.wait(other, 5).status == "finished"
    runner.answer(first, "w", "done")
    runner.wait(first, 5)
    assert runner.wait(runner.submit("test", "Third", lambda job: {}), 5).status == "finished"


def test_another_process_can_answer_and_cancel_through_the_mailbox(tmp_path):
    server = _runner(tmp_path)

    def waits(job):
        with job.step("w", "Wait"):
            job.wait_for_user("hold")
        return {"ok": True}

    job_id = server.submit("test", "Mailbox", waits, exclusive="")
    _until(lambda: _waiting_on(server, job_id) == "w")
    cli = JobRunner(tmp_path / "jobs")
    cli.answer(job_id, "w", "done")
    assert server.wait(job_id, 5).status == "finished"

    second = server.submit("test", "Cancel", waits, exclusive="")
    _until(lambda: _waiting_on(server, second) == "w")
    assert cli.cancel(second) is True
    assert server.wait(second, 5).status == "cancelled"


def test_recover_marks_jobs_left_behind_as_interrupted(tmp_path):
    old_process = _runner(tmp_path)

    def waits(job):
        with job.step("w", "Wait"):
            job.wait_for_user("hold")

    job_id = old_process.submit("test", "Orphan", waits)
    _until(lambda: _waiting_on(old_process, job_id) == "w")

    new_process = JobRunner(tmp_path / "jobs")
    assert new_process.recover() == [job_id]
    assert new_process.get(job_id).status == "interrupted"
    assert new_process.events(job_id)[-1].kind == "job.interrupted"
    old_process.cancel(job_id)
    old_process.wait(job_id, 5)


def test_resume_skips_steps_whose_artifacts_are_unchanged(tmp_path):
    runner = _runner(tmp_path)
    artifact = tmp_path / "made.txt"
    calls = []
    gate = {"ok": False}

    def factory(spec):
        def work(job):
            if job.completed("make") is not None:
                job.skip("make", "Make", "reused")
            else:
                with job.step("make", "Make") as handle:
                    artifact.write_text("made", encoding="utf-8")
                    handle.artifact("out", artifact)
                    calls.append("make")
            with job.step("finish", "Finish"):
                if not gate["ok"]:
                    raise RuntimeError("not yet")
            return {}

        return work

    first = runner.submit("test", "Resumable", factory({}))
    assert runner.wait(first, 5).status == "failed"
    with pytest.raises(ValueError):
        runner.resume(runner.submit("test", "done", lambda job: {}, exclusive=""), factory)

    gate["ok"] = True
    second = runner.resume(first, factory)
    status = runner.wait(second, 5)
    assert status.status == "finished" and status.resumed_from == first
    assert calls == ["make"]
    assert status.step("make").status == "skipped"

    artifact.write_text("tampered", encoding="utf-8")
    gate["ok"] = False
    third = runner.submit("test", "Again", factory({}))
    runner.wait(third, 5)
    gate["ok"] = True
    artifact.write_text("changed after", encoding="utf-8")
    runner.wait(runner.resume(third, factory), 5)
    assert calls == ["make", "make", "make"]
