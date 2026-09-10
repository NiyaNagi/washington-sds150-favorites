"""Render a fleet radio's inputs and checklist as Markdown, and keep the
generated sections of ``docs/fleet-updates.md`` in step with the registry."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Mapping, Optional

from wasds150.fleet.model import STEP_AUTO, STEP_CONFIRM, FleetRadio, render_instructions
from wasds150.fleet.registry import FLEET
from wasds150.radios.registry import get_profile

_KIND_LABEL = {STEP_AUTO: "automatic", STEP_CONFIRM: "confirm"}


def _begin(radio_id: str) -> str:
    return f"<!-- fleet:begin {radio_id} -->"


def _end(radio_id: str) -> str:
    return f"<!-- fleet:end {radio_id} -->"


def default_values(radio: FleetRadio) -> Dict[str, str]:
    """Placeholder values known without running anything."""
    from wasds150.plans.template import default_knobs

    return {"plan_id": radio.plan_id, "callsign": default_knobs(radio.radio_id).callsign}


def render_markdown(radio: FleetRadio, values: Optional[Mapping[str, str]] = None) -> str:
    context = dict(default_values(radio))
    context.update(values or {})
    profile = get_profile(radio.radio_id)
    lines: List[str] = [f"### {profile.label} (`{radio.radio_id}`)", ""]
    if radio.plan_id:
        lines.append(f"- Built from plan `{radio.plan_id}`, exported as `{radio.target_id}`.")
    else:
        lines.append("- Built from every enabled, populated Favorites List in the catalog.")
    lines.append(
        "- Loaded **automatically**." if not radio.guided
        else "- **Prepared and guided**: the wizard exports and opens the vendor program, "
        "then waits for you at each manual step."
    )
    if radio.vendor_app is not None:
        lines.append(f"- Vendor program: {radio.vendor_app.label}.")
    lines.append(f"- Verification: {radio.verify}.")
    if radio.notes:
        lines.append(f"- {radio.notes}")
    if radio.inputs:
        lines += ["", "| Setting | Required | Default | Notes |", "|---|---|---|---|"]
        for spec in radio.inputs:
            lines.append(
                f"| `{radio.radio_id}.{spec.id}` ({spec.label}) | {'yes' if spec.required else 'no'} "
                f"| {('`' + spec.default + '`') if spec.default else ''} | {spec.help} |"
            )
    lines.append("")
    for number, step in enumerate(radio.steps, start=1):
        tags = [t for t in (_KIND_LABEL.get(step.kind), "optional" if step.optional else "") if t]
        suffix = f" _({', '.join(tags)})_" if tags else ""
        text = render_instructions(step.instructions, context)
        lines.append(f"{number}. **{step.title}**{suffix} - {text}")
    return "\n".join(lines).rstrip() + "\n"


def render_section(radio: FleetRadio) -> str:
    return f"{_begin(radio.radio_id)}\n{render_markdown(radio)}{_end(radio.radio_id)}"


def sync_text(text: str, radio: FleetRadio) -> str:
    """Replace ``radio``'s generated section in ``text``; append it if absent."""
    pattern = re.compile(re.escape(_begin(radio.radio_id)) + r".*?" + re.escape(_end(radio.radio_id)), re.DOTALL)
    section = render_section(radio)
    if pattern.search(text):
        return pattern.sub(lambda _m: section, text, count=1)
    return text.rstrip("\n") + "\n\n" + section + "\n"


def stale_docs(repo_root: Path) -> List[str]:
    """Radio ids whose generated doc section differs from the registry."""
    stale: List[str] = []
    for radio in FLEET.values():
        if not radio.doc:
            continue
        path = Path(repo_root) / radio.doc
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if sync_text(text, radio) != text:
            stale.append(radio.radio_id)
    return stale


def write_docs(repo_root: Path) -> List[Path]:
    written: List[Path] = []
    for radio in FLEET.values():
        if not radio.doc:
            continue
        path = Path(repo_root) / radio.doc
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        updated = sync_text(text, radio)
        if updated != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(updated, encoding="utf-8")
            if path not in written:
                written.append(path)
    return written
