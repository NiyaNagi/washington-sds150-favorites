"""``wasds150 fleet audit``: every transmitting radio's plan and exported file,
checked before anything is written to a radio (see :mod:`wasds150.plan.audit`).

The SDS150 is receive only and is not audited here.
"""
from __future__ import annotations

import datetime
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from wasds150.appctx import AppContext
from wasds150.plan.audit import ERROR, WARNING, Finding, audit_export, audit_plan


@dataclass
class FleetAudit:
    findings: List[Finding] = field(default_factory=list)
    radios: List[str] = field(default_factory=list)
    coordination_date: str = ""
    coordination_records: int = 0

    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == ERROR]

    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.severity == WARNING]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "radios": list(self.radios),
            "coordination_date": self.coordination_date,
            "coordination_records": self.coordination_records,
            "errors": len(self.errors()),
            "warnings": len(self.warnings()),
            "findings": [f.to_dict() for f in self.findings],
        }

    def summary_lines(self) -> List[str]:
        lines = []
        if self.coordination_records:
            lines.append(f"WWARA coordination {self.coordination_date}: {self.coordination_records} records")
        else:
            lines.append("WWARA coordination: not cached - refresh sources to check calls, inputs and tones")
        for radio in self.radios:
            counts = Counter(f.severity for f in self.findings if f.radio_id == radio)
            lines.append(f"{radio:10} {counts.get(ERROR, 0):4} error(s) {counts.get(WARNING, 0):4} warning(s)")
        return lines

    def to_markdown(self) -> str:
        lines = [f"# Radio audit - {datetime.date.today().isoformat()}", ""]
        lines += [f"- {line}" for line in self.summary_lines()]
        lines.append("")
        for title, rows in (("Errors", self.errors()), ("Warnings", self.warnings())):
            lines += [f"## {title} ({len(rows)})", ""]
            by_code: Dict[str, List[Finding]] = {}
            for finding in rows:
                by_code.setdefault(finding.code, []).append(finding)
            for code, items in sorted(by_code.items()):
                lines += [f"### {code} ({len(items)})", ""]
                lines += [f"- {item.line()}" for item in items]
                lines.append("")
        return "\n".join(lines)


def audit_fleet(ctx: AppContext, radio_ids: Iterable[str], *, include_licensed: bool = True) -> FleetAudit:
    from wasds150.export.registry import get_target
    from wasds150.fleet.registry import get_fleet_radio
    from wasds150.paths import exports_dir
    from wasds150.plan.coordination import load_coordination
    from wasds150.plan.service import resolve_named_plan

    coordination = load_coordination(ctx.config)
    audit = FleetAudit(
        coordination_date=coordination.source_date if coordination else "",
        coordination_records=len(coordination) if coordination else 0,
    )
    for radio_id in radio_ids:
        radio = get_fleet_radio(radio_id)
        if not radio.plan_id:
            continue
        audit.radios.append(radio.radio_id)
        plan, resolved = resolve_named_plan(ctx, radio.plan_id, include_licensed=include_licensed)
        audit.findings += audit_plan(radio.radio_id, resolved, coordination)
        exported = exports_dir(radio.radio_id) / f"{plan.id}{get_target(radio.target_id).extension}"
        if exported.exists():
            audit.findings += audit_export(radio.radio_id, resolved, exported)
    return audit
