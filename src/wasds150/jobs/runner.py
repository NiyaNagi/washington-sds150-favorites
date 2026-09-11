"""Run jobs on threads, persist their events, and let an operator answer them.

One thread per job. A job that stops for the operator blocks on its own
answer queue; the CLI or a web request delivers the answer. When the job
runs in another process (the web server) and the answer comes from the CLI,
it goes through a mailbox file beside the job's event log, which the waiting
job polls - the same for cancellation - so ``wasds150 jobs answer`` works
against a job the browser started.

Jobs in an exclusive group (``"fleet"``) run one at a time: two updates
programming the same radios, or swapping the catalog under each other, is
exactly the race the group exists to prevent.

A process that dies mid-job leaves a status document saying ``running``;
:meth:`JobRunner.recover` marks those ``interrupted`` at startup, and
:meth:`JobRunner.resume` starts a new job that skips the steps whose
artifacts are still on disk unchanged.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import queue
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from wasds150.jobs.events import (
    ACTIVE,
    CANCELLED,
    FAILED,
    FINISHED,
    INTERRUPTED,
    JOB_CANCELLED,
    JOB_FAILED,
    JOB_FINISHED,
    JOB_INTERRUPTED,
    JOB_STARTED,
    QUEUED,
    RUNNING,
    STEP_DONE,
    SYNC_KINDS,
    WAITING,
    Answer,
    JobEvent,
    JobStatus,
    now_iso,
)
from wasds150.util.hashing import sha256_of_path

logger = logging.getLogger("wasds150.jobs")

JobFn = Callable[["JobContext"], Optional[Dict[str, Any]]]


class JobBusy(RuntimeError):
    """Another job in the same exclusive group is still active."""

    def __init__(self, job_id: str, group: str):
        super().__init__(f"job {job_id} is already running in group {group!r}")
        self.job_id = job_id
        self.group = group


class JobCancelled(Exception):
    """Raised inside a job when it was cancelled or the operator aborted."""


class _Job:
    def __init__(self, status: JobStatus):
        self.status = status
        self.events: List[JobEvent] = []
        self.cancel = threading.Event()
        self.answers: "queue.Queue[Tuple[str, Answer]]" = queue.Queue()
        self.lock = threading.RLock()
        self.thread: Optional[threading.Thread] = None
        self.mailbox_offset = 0


def _new_job_id() -> str:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


def artifacts_intact(data: Dict[str, Any]) -> bool:
    """True when every artifact a step recorded still exists unchanged."""
    for artifact in (data.get("artifacts") or {}).values():
        path = Path(artifact.get("path", ""))
        if not path.exists() or sha256_of_path(path) != artifact.get("sha256"):
            return False
    return True


class JobRunner:
    #: How often a waiting job checks for cancellation and mailbox answers.
    POLL_SECONDS = 0.2

    def __init__(self, jobs_dir: Path):
        self.jobs_dir = Path(jobs_dir)
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._jobs: Dict[str, _Job] = {}
        self._groups: Dict[str, str] = {}

    # ------------------------------------------------------------ paths --
    def _status_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def _events_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.jsonl"

    def _mailbox_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.answers.jsonl"

    def _cancel_path(self, job_id: str) -> Path:
        return self.jobs_dir / f"{job_id}.cancel"

    @staticmethod
    def _valid_id(job_id: str) -> str:
        if not job_id or any(c in job_id for c in "/\\.:") or len(job_id) > 64:
            raise KeyError(f"no such job: {job_id!r}")
        return job_id

    # ------------------------------------------------------ persistence --
    def _write_status(self, job: _Job) -> None:
        path = self._status_path(job.status.job_id)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(job.status.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
        os.replace(tmp, path)

    def emit(self, job: _Job, kind: str, *, step_id: str = "", message: str = "",
             data: Optional[Dict[str, Any]] = None) -> JobEvent:
        with job.lock:
            seq = job.status.last_seq + 1
            event = JobEvent(seq, now_iso(), job.status.job_id, kind, step_id, message, dict(data or {}))
            job.events.append(event)
            job.status.last_seq = seq
            with self._events_path(job.status.job_id).open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(event.to_dict(), sort_keys=True, default=str) + "\n")
                fh.flush()
                if kind in SYNC_KINDS:
                    os.fsync(fh.fileno())
            self._write_status(job)
        return event

    def _update(self, job: _Job, mutate: Callable[[JobStatus], None]) -> None:
        with job.lock:
            mutate(job.status)
            self._write_status(job)

    # ------------------------------------------------------------- run --
    def submit(
        self,
        kind: str,
        title: str,
        fn: JobFn,
        *,
        spec: Optional[Dict[str, Any]] = None,
        exclusive: str = "fleet",
        resumed_from: str = "",
    ) -> str:
        with self._lock:
            if exclusive:
                holder = self._groups.get(exclusive)
                if holder and self._jobs[holder].status.active:
                    raise JobBusy(holder, exclusive)
            job_id = _new_job_id()
            job = _Job(
                JobStatus(
                    job_id=job_id, kind=kind, title=title, status=QUEUED, created_at=now_iso(),
                    spec=dict(spec or {}), resumed_from=resumed_from,
                )
            )
            self._jobs[job_id] = job
            if exclusive:
                self._groups[exclusive] = job_id
            self._write_status(job)
            job.thread = threading.Thread(target=self._run, args=(job, fn), name=f"job-{job_id}", daemon=True)
            job.thread.start()
        return job_id

    def _run(self, job: _Job, fn: JobFn) -> None:
        from wasds150.jobs.context import JobContext

        context = JobContext(self, job)
        self._update(job, lambda s: (setattr(s, "status", RUNNING), setattr(s, "started_at", now_iso())))
        self.emit(job, JOB_STARTED, message=job.status.title)
        try:
            result = fn(context) or {}
        except JobCancelled as exc:
            context._close_open_steps("cancelled")
            self._finish(job, CANCELLED, error=str(exc) or "cancelled")
            self.emit(job, JOB_CANCELLED, message=str(exc) or "cancelled")
        except Exception as exc:  # noqa: BLE001 - a job failure must never kill the server
            logger.exception("job %s failed", job.status.job_id)
            context._close_open_steps(f"{type(exc).__name__}: {exc}")
            self._finish(job, FAILED, error=f"{type(exc).__name__}: {exc}")
            self.emit(job, JOB_FAILED, message=f"{type(exc).__name__}: {exc}")
        else:
            self._finish(job, FINISHED, result=result)
            self.emit(job, JOB_FINISHED, message="finished", data={"result": result})

    def _finish(self, job: _Job, status: str, *, error: str = "", result: Optional[Dict[str, Any]] = None) -> None:
        def mutate(s: JobStatus) -> None:
            s.status = status
            s.finished_at = now_iso()
            s.waiting = None
            s.error = error
            if result is not None:
                s.result = result

        self._update(job, mutate)

    # ----------------------------------------------------------- query --
    def get(self, job_id: str) -> JobStatus:
        job = self._jobs.get(job_id)
        if job is not None:
            with job.lock:
                return JobStatus.from_dict(job.status.to_dict())
        path = self._status_path(self._valid_id(job_id))
        if not path.exists():
            raise KeyError(f"no such job: {job_id!r}")
        return JobStatus.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def events(self, job_id: str, since_seq: int = 0) -> List[JobEvent]:
        job = self._jobs.get(job_id)
        if job is not None:
            with job.lock:
                return [e for e in job.events if e.seq > since_seq]
        path = self._events_path(self._valid_id(job_id))
        if not path.exists():
            if not self._status_path(job_id).exists():
                raise KeyError(f"no such job: {job_id!r}")
            return []
        events = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = JobEvent.from_dict(json.loads(line))
                if event.seq > since_seq:
                    events.append(event)
        return events

    def list(self) -> List[JobStatus]:
        statuses: Dict[str, JobStatus] = {}
        for path in self.jobs_dir.glob("*.json"):
            try:
                status = JobStatus.from_dict(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
            statuses[status.job_id] = status
        for job_id in list(self._jobs):
            statuses[job_id] = self.get(job_id)
        return sorted(statuses.values(), key=lambda s: s.created_at, reverse=True)

    def wait(self, job_id: str, timeout: Optional[float] = None) -> JobStatus:
        job = self._jobs.get(job_id)
        if job is not None and job.thread is not None:
            job.thread.join(timeout)
        return self.get(job_id)

    # ------------------------------------------------------- operator --
    def answer(self, job_id: str, step_id: str, decision: str, inputs: Optional[Dict[str, str]] = None) -> None:
        answer = Answer(decision, {str(k): str(v) for k, v in (inputs or {}).items()})
        status = self.get(job_id)
        if status.status != WAITING or not status.waiting or status.waiting.get("step_id") != step_id:
            raise ValueError(f"job {job_id} is not waiting on step {step_id!r}")
        job = self._jobs.get(job_id)
        if job is not None:
            job.answers.put((step_id, answer))
            return
        with self._mailbox_path(job_id).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"step_id": step_id, "decision": answer.decision, "inputs": answer.inputs}) + "\n")

    def cancel(self, job_id: str) -> bool:
        status = self.get(job_id)
        if not status.active:
            return False
        job = self._jobs.get(job_id)
        if job is not None:
            job.cancel.set()
        else:
            self._cancel_path(job_id).write_text(now_iso(), encoding="utf-8")
        return True

    def cancel_requested(self, job: _Job) -> bool:
        return job.cancel.is_set() or self._cancel_path(job.status.job_id).exists()

    def next_answer(self, job: _Job, step_id: str) -> Optional[Answer]:
        """One poll for an answer to ``step_id``: the in-process queue, then
        the mailbox file another process may have written."""
        try:
            got_step, answer = job.answers.get(timeout=self.POLL_SECONDS)
            if got_step == step_id:
                return answer
        except queue.Empty:
            pass
        path = self._mailbox_path(job.status.job_id)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as fh:
            fh.seek(job.mailbox_offset)
            while True:
                line = fh.readline()
                if not line:
                    break
                job.mailbox_offset = fh.tell()
                try:
                    data = json.loads(line)
                    if data.get("step_id") == step_id:
                        return Answer(data.get("decision", ""), dict(data.get("inputs") or {}))
                except ValueError:
                    continue
        return None

    # ---------------------------------------------------------- restart --
    def recover(self) -> List[str]:
        """Mark jobs a previous process left active as interrupted."""
        interrupted = []
        for status in self.list():
            if status.job_id in self._jobs or not status.active:
                continue
            job = _Job(status)
            job.status.status = INTERRUPTED
            job.status.finished_at = now_iso()
            job.status.waiting = None
            job.status.error = "the process running this job stopped"
            self.emit(job, JOB_INTERRUPTED, message=job.status.error)
            interrupted.append(status.job_id)
        return interrupted

    def resume(
        self,
        job_id: str,
        fn_factory: Callable[[Dict[str, Any]], JobFn],
        *,
        exclusive: str = "fleet",
    ) -> str:
        """Start a new job from ``job_id``'s spec, skipping its completed steps
        whose artifacts are still on disk unchanged."""
        old = self.get(job_id)
        if old.status not in (FAILED, CANCELLED, INTERRUPTED):
            raise ValueError(f"job {job_id} is {old.status}; only a stopped job can be resumed")
        completed = {
            step.id: step.data for step in old.steps if step.status == STEP_DONE and artifacts_intact(step.data)
        }
        spec = dict(old.spec)
        spec["completed_steps"] = sorted(completed)
        spec["completed_data"] = completed
        return self.submit(old.kind, old.title, fn_factory(spec), spec=spec, exclusive=exclusive, resumed_from=job_id)
