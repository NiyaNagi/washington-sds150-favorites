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


#: Every radio's capabilities, rendered from its profile (wasds150.radios).
CAPABILITY_DOC = "docs/radio-capabilities.md"


def _bands(bands) -> str:
    return ", ".join(f"{low:g}-{high:g}" for low, high in bands) + " MHz" if bands else "none (receive only)"


def render_capabilities() -> str:
    """docs/radio-capabilities.md: what each radio can do, and where that
    came from. The audit (``fleet audit``) checks every memory against it."""
    from wasds150.radios.registry import list_profiles

    profiles = [p for _id, p in sorted(list_profiles().items())]
    lines: List[str] = [
        "# Radio capabilities",
        "",
        "Generated from the radio profiles in `src/wasds150/radios/registry.py` by "
        "`wasds150 fleet docs`; do not edit by hand. Every plan picks stations by these "
        "capabilities, and `wasds150 fleet audit` fails a memory the radio cannot hold "
        "(`capability-violation`), a D-STAR machine on a radio without D-STAR "
        "(`dstar-unsupported`) and a D-STAR machine programmed as FM (`dstar-as-analog`).",
        "",
        "| Radio | D-STAR | C4FM | DMR | NXDN | P25 | AM | Transmit | Verified |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for p in profiles:
        def has(mode: str) -> str:
            return "yes" if p.supports_mode(mode) else "-"

        am_limits = [bands for mode, bands in p.mode_bands if mode == "AM"]
        am = ("" if not p.supports_mode("AM") else _bands(am_limits[0]) if am_limits else "all receive bands")
        lines.append(
            f"| {p.label} | {has('DV')} | {has('C4FM')} | {has('DMR')} | {has('NXDN')} | {has('P25')} "
            f"| {am or '-'} | {_bands(p.tx_bands)} | {'yes' if p.verified else 'no'} ({p.verified_on or 'never'}) |"
        )
    for p in profiles:
        lines += ["", f"## {p.label} (`{p.id}`)", ""]
        lines.append(f"- Receive: {_bands(p.rx_bands)}")
        lines.append(f"- Transmit (hardware; licence decides use): {_bands(p.tx_bands)}")
        lines.append(f"- Modes: {', '.join(sorted(p.modes))}")
        for mode, bands in p.mode_bands:
            lines.append(f"- {mode} only on: {_bands(bands)}")
        memory = f"{p.max_channels:,} channels" if p.max_channels else "no fixed channel ceiling"
        if p.zone_max:
            memory += f"; {p.zone_max} groups/zones of up to {p.zone_member_max}"
        if p.scan_list_member_max:
            memory += f"; scan lists of up to {p.scan_list_member_max}"
        if not p.supports_banks:
            memory += "; no groups (memory order is the scan)"
        lines.append(f"- Memory: {memory}; names up to {p.name_max_len or 'any'} characters")
        if p.contacts is not None:
            lines.append(f"- Contacts: {', '.join(sorted(p.contacts.protocols))}, up to {p.contacts.max_contacts:,}")
        lines.append(f"- Notes: {p.notes}")
        lines.append(f"- Verified: {'yes' if p.verified else 'no'}, checked {p.verified_on or 'never'}")
        lines.append("- Sources:")
        lines += [f"  - {source}" for source in p.sources]
    return "\n".join(lines) + "\n"


def stale_docs(repo_root: Path) -> List[str]:
    """Radio ids whose generated doc section differs from the registry, and
    ``capabilities`` when docs/radio-capabilities.md is out of date."""
    stale: List[str] = []
    for radio in FLEET.values():
        if not radio.doc:
            continue
        path = Path(repo_root) / radio.doc
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if sync_text(text, radio) != text:
            stale.append(radio.radio_id)
    capabilities = Path(repo_root) / CAPABILITY_DOC
    if not capabilities.exists() or capabilities.read_text(encoding="utf-8") != render_capabilities():
        stale.append("capabilities")
    return stale


def write_docs(repo_root: Path) -> List[Path]:
    written: List[Path] = []
    capabilities = Path(repo_root) / CAPABILITY_DOC
    text = render_capabilities()
    if not capabilities.exists() or capabilities.read_text(encoding="utf-8") != text:
        capabilities.parent.mkdir(parents=True, exist_ok=True)
        capabilities.write_text(text, encoding="utf-8")
        written.append(capabilities)
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
