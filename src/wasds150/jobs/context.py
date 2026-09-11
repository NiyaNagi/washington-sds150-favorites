"""The API a job's code uses: steps, progress, logs, and stopping for the
operator."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from wasds150.jobs.events import (
    DECISION_ABORT,
    DECISION_SKIP,
    INPUT_REQUIRED,
    RUNNING,
    STEP_DONE,
    STEP_FAILED,
    STEP_FAILED_STATE,
    STEP_FINISHED,
    STEP_LOG,
    STEP_PROGRESS,
    STEP_RUNNING,
    STEP_SKIPPED,
    STEP_SKIPPED_STATE,
    STEP_STARTED,
    STEP_WAITING,
    STEP_WAITING_STATE,
    WAITING,
    Answer,
    now_iso,
)
from wasds150.jobs.runner import JobCancelled, JobRunner, _Job
from wasds150.util.hashing import sha256_of_path


class StepSkipped(Exception):
    """Raise inside :meth:`JobContext.step` to record the step as skipped."""


class StepHandle:
    def __init__(self) -> None:
        self.message = ""
        self.data: Dict[str, Any] = {}

    def artifact(self, name: str, path: Path) -> None:
        """Record a file or directory this step produced, with its hash, so a
        resumed job can reuse it only if it is unchanged."""
        path = Path(path)
        self.data.setdefault("artifacts", {})[name] = {"path": str(path), "sha256": sha256_of_path(path)}


class JobContext:
    def __init__(self, runner: JobRunner, job: _Job):
        self._runner = runner
        self._job = job
        self._open: List[str] = []

    @property
    def job_id(self) -> str:
        return self._job.status.job_id

    @property
    def spec(self) -> Dict[str, Any]:
        return self._job.status.spec

    def completed(self, step_id: str) -> Optional[Dict[str, Any]]:
        """The data of ``step_id`` from the job this one resumes, if it
        finished there and its artifacts are unchanged."""
        if step_id in (self.spec.get("completed_steps") or []):
            return (self.spec.get("completed_data") or {}).get(step_id, {})
        return None

    # ---------------------------------------------------------- events --
    def _current(self) -> str:
        return self._open[-1] if self._open else ""

    def emit(self, kind: str, message: str = "", *, step_id: Optional[str] = None,
             data: Optional[Dict[str, Any]] = None) -> None:
        self._runner.emit(self._job, kind, step_id=self._current() if step_id is None else step_id,
                          message=message, data=data)

    def log(self, message: str, **data: Any) -> None:
        self.emit(STEP_LOG, message, data=data or None)

    def progress(self, message: str = "", done: Optional[int] = None, total: Optional[int] = None) -> None:
        self.emit(STEP_PROGRESS, message, data={"done": done, "total": total})

    def cancelled(self) -> bool:
        """For code that must stop a subprocess rather than raise."""
        return self._runner.cancel_requested(self._job)

    def check_cancelled(self) -> None:
        if self.cancelled():
            raise JobCancelled("cancelled")

    # ----------------------------------------------------------- steps --
    def _set_step(self, step_id: str, title: str, optional: bool, **changes: Any) -> None:
        def mutate(status: Any) -> None:
            state = status.upsert_step(step_id, title, optional)
            for key, value in changes.items():
                setattr(state, key, value)

        self._runner._update(self._job, mutate)

    @contextmanager
    def step(self, step_id: str, title: str, *, optional: bool = False) -> Iterator[StepHandle]:
        self.check_cancelled()
        self._set_step(step_id, title, optional, status=STEP_RUNNING, started_at=now_iso(), message="")
        self._open.append(step_id)
        self.emit(STEP_STARTED, title)
        handle = StepHandle()
        try:
            yield handle
        except StepSkipped as exc:
            self._set_step(step_id, title, optional, status=STEP_SKIPPED_STATE, finished_at=now_iso(),
                           message=str(exc), data=handle.data)
            self.emit(STEP_SKIPPED, str(exc))
        except JobCancelled:
            self._set_step(step_id, title, optional, status=STEP_FAILED_STATE, finished_at=now_iso(),
                           message="cancelled", data=handle.data)
            raise
        except Exception as exc:
            self._set_step(step_id, title, optional, status=STEP_FAILED_STATE, finished_at=now_iso(),
                           message=f"{type(exc).__name__}: {exc}", data=handle.data)
            self.emit(STEP_FAILED, f"{type(exc).__name__}: {exc}")
            raise
        else:
            self._set_step(step_id, title, optional, status=STEP_DONE, finished_at=now_iso(),
                           message=handle.message, data=handle.data)
            self.emit(STEP_FINISHED, handle.message or "done", data=handle.data or None)
        finally:
            if self._open and self._open[-1] == step_id:
                self._open.pop()

    def skip(self, step_id: str, title: str, reason: str, *, optional: bool = False) -> None:
        """Record a step that is not run at all this time."""
        self._set_step(step_id, title, optional, status=STEP_SKIPPED_STATE, finished_at=now_iso(), message=reason)
        self.emit(STEP_SKIPPED, reason, step_id=step_id)

    def _close_open_steps(self, message: str) -> None:
        for step_id in list(self._open):
            state = self._job.status.step(step_id)
            if state is not None and state.status in (STEP_RUNNING, STEP_WAITING_STATE):
                self._set_step(step_id, state.title, state.optional, status=STEP_FAILED_STATE,
                               finished_at=now_iso(), message=message)
        self._open.clear()

    # -------------------------------------------------------- operator --
    def wait_for_user(
        self,
        instructions: str,
        *,
        title: str = "",
        kind: str = "manual",
        inputs: Sequence[Dict[str, Any]] = (),
        artifacts: Optional[Dict[str, str]] = None,
    ) -> Answer:
        """Stop the current step until the operator answers.

        ``abort`` raises :class:`JobCancelled`; ``skip`` and ``done`` are
        returned for the caller to act on.
        """
        step_id = self._current()
        state = self._job.status.step(step_id)
        step_title = title or (state.title if state else step_id)
        waiting = {
            "step_id": step_id,
            "title": step_title,
            "instructions": instructions,
            "kind": kind,
            "inputs": list(inputs),
            "artifacts": dict(artifacts or {}),
        }

        def enter(status: Any) -> None:
            status.status = WAITING
            status.waiting = waiting
            current = status.step(step_id)
            if current is not None:
                current.status = STEP_WAITING_STATE

        self._runner._update(self._job, enter)
        self.emit(INPUT_REQUIRED if inputs else STEP_WAITING, instructions, data=waiting)
        try:
            while True:
                if self._runner.cancel_requested(self._job):
                    raise JobCancelled("cancelled")
                answer = self._runner.next_answer(self._job, step_id)
                if answer is None:
                    continue
                if answer.decision == DECISION_ABORT:
                    raise JobCancelled(f"aborted by the operator at {step_id}")
                return answer
        finally:
            def leave(status: Any) -> None:
                status.waiting = None
                if status.status == WAITING:
                    status.status = RUNNING
                current = status.step(step_id)
                if current is not None and current.status == STEP_WAITING_STATE:
                    current.status = STEP_RUNNING

            self._runner._update(self._job, leave)

    def require_input(self, spec: Dict[str, Any], current: str = "") -> str:
        """``current`` if set, else ask the operator for it. A skipped
        request returns an empty string."""
        if current:
            return current
        answer = self.wait_for_user(
            spec.get("help") or f"Enter {spec.get('label', spec['id'])}",
            kind="input",
            inputs=[spec],
        )
        if answer.decision == DECISION_SKIP:
            return ""
        return str(answer.inputs.get(spec["id"], "")).strip()
