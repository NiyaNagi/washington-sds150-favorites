"""Job events and status documents.

A job is described by two files under ``state/jobs/``: ``<id>.jsonl``, an
append-only log of :class:`JobEvent` records that clients poll with
``since=<seq>``, and ``<id>.json``, a :class:`JobStatus` snapshot rewritten
atomically on every change. The log is the history; the snapshot answers
"what is it doing now" without replaying the log.
"""
from __future__ import annotations

import datetime
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

JOB_STARTED = "job.started"
JOB_FINISHED = "job.finished"
JOB_FAILED = "job.failed"
JOB_CANCELLED = "job.cancelled"
JOB_INTERRUPTED = "job.interrupted"
STEP_STARTED = "step.started"
STEP_PROGRESS = "step.progress"
STEP_LOG = "step.log"
STEP_FINISHED = "step.finished"
STEP_FAILED = "step.failed"
STEP_SKIPPED = "step.skipped"
STEP_WAITING = "step.waiting"
INPUT_REQUIRED = "input.required"
CATALOG_DELTA = "catalog.delta"
RADIO_DIFF = "radio.diff"

EVENT_KINDS = (
    JOB_STARTED, JOB_FINISHED, JOB_FAILED, JOB_CANCELLED, JOB_INTERRUPTED,
    STEP_STARTED, STEP_PROGRESS, STEP_LOG, STEP_FINISHED, STEP_FAILED, STEP_SKIPPED, STEP_WAITING,
    INPUT_REQUIRED, CATALOG_DELTA, RADIO_DIFF,
)

#: Events written with an fsync: the boundaries a restart must not lose.
SYNC_KINDS = frozenset(
    {JOB_STARTED, JOB_FINISHED, JOB_FAILED, JOB_CANCELLED, JOB_INTERRUPTED,
     STEP_FINISHED, STEP_FAILED, STEP_SKIPPED, STEP_WAITING, INPUT_REQUIRED}
)

QUEUED = "queued"
RUNNING = "running"
WAITING = "waiting"
FINISHED = "finished"
FAILED = "failed"
CANCELLED = "cancelled"
INTERRUPTED = "interrupted"
ACTIVE = (QUEUED, RUNNING, WAITING)
TERMINAL = (FINISHED, FAILED, CANCELLED, INTERRUPTED)

STEP_PENDING = "pending"
STEP_RUNNING = "running"
STEP_WAITING_STATE = "waiting"
STEP_DONE = "finished"
STEP_FAILED_STATE = "failed"
STEP_SKIPPED_STATE = "skipped"

DECISION_DONE = "done"
DECISION_SKIP = "skip"
DECISION_ABORT = "abort"
DECISIONS = (DECISION_DONE, DECISION_SKIP, DECISION_ABORT)


def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds")


@dataclass
class JobEvent:
    seq: int
    ts: str
    job_id: str
    kind: str
    step_id: str = ""
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobEvent":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class StepState:
    id: str
    title: str
    status: str = STEP_PENDING
    started_at: str = ""
    finished_at: str = ""
    message: str = ""
    optional: bool = False
    #: What the step produced; ``data["artifacts"]`` maps a name to
    #: ``{"path", "sha256"}`` so a resumed job can tell whether it still holds.
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepState":
        known = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class JobStatus:
    job_id: str
    kind: str
    title: str
    status: str = QUEUED
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    last_seq: int = 0
    steps: List[StepState] = field(default_factory=list)
    #: What the job is waiting for, while ``status == "waiting"``:
    #: ``{"step_id", "title", "instructions", "kind", "inputs", "artifacts"}``.
    waiting: Optional[Dict[str, Any]] = None
    error: str = ""
    spec: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    resumed_from: str = ""

    def step(self, step_id: str) -> Optional[StepState]:
        for state in self.steps:
            if state.id == step_id:
                return state
        return None

    def upsert_step(self, step_id: str, title: str, optional: bool = False) -> StepState:
        state = self.step(step_id)
        if state is None:
            state = StepState(id=step_id, title=title, optional=optional)
            self.steps.append(state)
        return state

    @property
    def active(self) -> bool:
        return self.status in ACTIVE

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["steps"] = [s.to_dict() for s in self.steps]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobStatus":
        known = set(cls.__dataclass_fields__)
        values = {k: v for k, v in data.items() if k in known}
        values["steps"] = [StepState.from_dict(s) for s in data.get("steps", [])]
        return cls(**values)


@dataclass
class Answer:
    decision: str
    inputs: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}")
