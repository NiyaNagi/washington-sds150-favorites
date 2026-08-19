"""Human-readable summary of what a plan put in a radio, and what it left out.

The drop list matters more than the channel list.  A plan that silently
discarded every 800 MHz talkgroup looks identical to one that worked; this
report is how that becomes visible before the radio is programmed.
"""
from __future__ import annotations

from typing import List

from wasds150.plan.resolve import ResolvedPlan

_REASON_EXPLANATIONS = {
    "no-rx-coverage": "outside the radio's receive coverage",
    "unsupported-mode": "the radio cannot demodulate this mode",
    "not-conventional": "trunked talkgroup with no tunable frequency",
    "duplicate": "the frequency is already programmed",
    "capacity": "the radio ran out of memory slots",
    "block-limit": "the plan capped this block",
}


def render_plan_report(resolved: ResolvedPlan, *, max_drops_per_reason: int = 8) -> str:
    profile = resolved.profile
    plan = resolved.plan
    lines: List[str] = []

    lines.append(f"# {plan.label}")
    lines.append("")
    lines.append(f"- Radio: {profile.label} ({profile.id})")
    if plan.description:
        lines.append(f"- Purpose: {plan.description}")
    capacity = resolved.capacity
    if capacity is None:
        lines.append(f"- Channels programmed: {resolved.slots_used}")
    else:
        free = capacity - resolved.slots_used
        lines.append(
            f"- Channels programmed: {resolved.slots_used} of {capacity} available"
            f" ({free} free, {plan.reserve_slots} reserved)"
        )
    lines.append(f"- Coverage: {profile.rx_coverage_summary()}")
    lines.append("")

    lines.append("## Memory map")
    lines.append("")
    lines.append("| Slots | Block | Channels | Transmit |")
    lines.append("| --- | --- | ---: | --- |")
    start = 1
    for block in plan.blocks:
        count = resolved.block_counts.get(block.label, 0)
        if count == 0:
            span = "-"
        else:
            span = f"{start}-{start + count - 1}" if count > 1 else str(start)
            start += count
        tx = {"none": "receive only", "simplex": "simplex", "repeater": "repeater"}[
            block.tx_policy
        ]
        lines.append(f"| {span} | {block.label} | {count} | {tx} |")
    lines.append("")

    lines.append("## Channels")
    lines.append("")
    lines.append("| # | Name | Receive | Transmit | Mode | Tone | Source |")
    lines.append("| ---: | --- | ---: | --- | --- | --- | --- |")
    for channel in resolved.channels:
        if not channel.transmit:
            tx = "RX only"
        elif channel.tx_freq_mhz is None:
            tx = "simplex"
        else:
            tx = f"{channel.tx_freq_mhz:.4f}"
        tone = channel.tx_tone.raw if channel.tx_tone.raw else "-"
        lines.append(
            f"| {channel.slot} | {channel.name} | {channel.rx_freq_mhz:.4f} | {tx} "
            f"| {channel.mode} | {tone} | {channel.source} |"
        )
    lines.append("")

    if resolved.warnings:
        lines.append("## Warnings")
        lines.append("")
        for warning in resolved.warnings:
            lines.append(f"- {warning}")
        lines.append("")

    if resolved.dropped:
        lines.append("## Excluded channels")
        lines.append("")
        lines.append(
            "Every catalog channel this plan matched but could not program, and why."
        )
        lines.append("")
        by_reason: dict = {}
        for item in resolved.dropped:
            by_reason.setdefault(item.reason, []).append(item)
        for reason in sorted(by_reason):
            items = by_reason[reason]
            explanation = _REASON_EXPLANATIONS.get(reason, reason)
            lines.append(f"### {reason} ({len(items)}) - {explanation}")
            lines.append("")
            for item in items[:max_drops_per_reason]:
                freq = f"{item.freq_mhz:.4f}" if item.freq_mhz is not None else "n/a"
                lines.append(f"- {item.label} [{freq}]")
            if len(items) > max_drops_per_reason:
                lines.append(f"- ... and {len(items) - max_drops_per_reason} more")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"
