"""What it takes to bring one radio up to date.

Each radio in the fleet reaches its memory by a different road: the SDS150
through a Sentinel workspace this project can write, the TD-H9 through a CHIRP
subprocess this project drives, and the TH-D75, FTX-1 and AT-D890UV through
vendor programs that only a person can click through. A :class:`FleetRadio`
describes that road as data - the inputs it needs, and an ordered list of
steps, each either run automatically or handed to the operator as a checklist
item - so the update wizard, the CLI and the generated docs all read one
description rather than three hand-maintained ones.

Step instructions may name placeholders in braces (``{export}``, ``{lst}``,
``{backup_d75}``); :func:`render_instructions` fills in what is known and
leaves the rest readable.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple

LOAD_AUTOMATED = "automated"
LOAD_GUIDED = "prepare-and-guide"
LOAD_PATHS = (LOAD_AUTOMATED, LOAD_GUIDED)

#: Run by the wizard itself.
STEP_AUTO = "auto"
#: Done by the operator in another program; the wizard waits for Done/Skip.
STEP_MANUAL = "manual"
#: A precondition the operator must confirm before automation continues
#: (Sentinel closed, cable plugged in).
STEP_CONFIRM = "confirm"
STEP_KINDS = (STEP_AUTO, STEP_MANUAL, STEP_CONFIRM)

VERIFY_READBACK = "readback"
VERIFY_HASH = "hash-compare"
VERIFY_NONE = "none"
VERIFY_KINDS = (VERIFY_READBACK, VERIFY_HASH, VERIFY_NONE)

INPUT_KINDS = ("com_port", "file", "dir", "app_path", "text")

_PLACEHOLDER = re.compile(r"\{([a-z0-9_]+)\}")


@dataclass(frozen=True)
class InputSpec:
    """A value the operator supplies once (saved in fleet settings)."""

    id: str
    kind: str
    label: str
    required: bool = True
    default: str = ""
    help: str = ""

    def __post_init__(self) -> None:
        if self.kind not in INPUT_KINDS:
            raise ValueError(f"input {self.id!r}: kind must be one of {INPUT_KINDS}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "label": self.label,
            "required": self.required,
            "default": self.default,
            "help": self.help,
        }


@dataclass(frozen=True)
class StepSpec:
    id: str
    title: str
    instructions: str
    kind: str = STEP_MANUAL
    #: Placeholder names (see module docstring) this step produces or uses,
    #: shown as links next to the checklist item.
    artifacts: Tuple[str, ...] = ()
    #: The operator may skip it without the update counting as incomplete.
    optional: bool = False
    #: This step is (part of) verifying what reached the radio.
    verify: bool = False

    def __post_init__(self) -> None:
        if self.kind not in STEP_KINDS:
            raise ValueError(f"step {self.id!r}: kind must be one of {STEP_KINDS}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "instructions": self.instructions,
            "kind": self.kind,
            "artifacts": list(self.artifacts),
            "optional": self.optional,
            "verify": self.verify,
        }


@dataclass(frozen=True)
class VendorApp:
    """A vendor programming application the operator finishes the job in."""

    id: str
    label: str
    exe_candidates: Tuple[str, ...] = ()
    #: True when the app accepts the exported file as a command-line argument.
    open_with_file: bool = False

    def find(self, override: str = "") -> Optional[Path]:
        """The first existing executable: ``override`` (from fleet settings)
        first, then the known install locations."""
        for candidate in ((override,) if override else ()) + self.exe_candidates:
            path = Path(os.path.expandvars(candidate))
            if path.is_file():
                return path
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "exe_candidates": list(self.exe_candidates),
            "open_with_file": self.open_with_file,
        }


@dataclass(frozen=True)
class FleetRadio:
    radio_id: str
    #: Channel plan the radio is built from; empty for the SDS150, which
    #: installs Favorites Lists instead of a flat memory plan.
    plan_id: str
    #: Export target id (see :mod:`wasds150.export.registry`); empty when the
    #: radio's content is not a plan export.
    target_id: str
    load_path: str
    inputs: Tuple[InputSpec, ...] = ()
    steps: Tuple[StepSpec, ...] = ()
    verify: str = VERIFY_NONE
    vendor_app: Optional[VendorApp] = None
    loadout_id: str = ""
    #: Repository doc that carries this radio's generated checklist.
    doc: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.load_path not in LOAD_PATHS:
            raise ValueError(f"{self.radio_id}: load_path must be one of {LOAD_PATHS}")
        if self.verify not in VERIFY_KINDS:
            raise ValueError(f"{self.radio_id}: verify must be one of {VERIFY_KINDS}")
        ids = [step.id for step in self.steps]
        if len(set(ids)) != len(ids):
            raise ValueError(f"{self.radio_id}: duplicate step ids")
        input_ids = [spec.id for spec in self.inputs]
        if len(set(input_ids)) != len(input_ids):
            raise ValueError(f"{self.radio_id}: duplicate input ids")

    @property
    def guided(self) -> bool:
        return self.load_path == LOAD_GUIDED

    def step(self, step_id: str) -> StepSpec:
        for step in self.steps:
            if step.id == step_id:
                return step
        raise KeyError(f"{self.radio_id}: no step {step_id!r}")

    def input(self, input_id: str) -> InputSpec:
        for spec in self.inputs:
            if spec.id == input_id:
                return spec
        raise KeyError(f"{self.radio_id}: no input {input_id!r}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "radio_id": self.radio_id,
            "plan_id": self.plan_id,
            "target_id": self.target_id,
            "load_path": self.load_path,
            "inputs": [spec.to_dict() for spec in self.inputs],
            "steps": [step.to_dict() for step in self.steps],
            "verify": self.verify,
            "vendor_app": self.vendor_app.to_dict() if self.vendor_app else None,
            "loadout_id": self.loadout_id,
            "doc": self.doc,
            "notes": self.notes,
        }


def render_instructions(text: str, values: Mapping[str, Any]) -> str:
    """Fill ``{name}`` placeholders from ``values``; unknown names are shown
    as ``<name>`` so a checklist printed before an export still reads."""

    def _sub(match: "re.Match[str]") -> str:
        value = values.get(match.group(1))
        return str(value) if value not in (None, "") else f"<{match.group(1)}>"

    return _PLACEHOLDER.sub(_sub, text)
