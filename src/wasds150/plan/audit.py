"""Check a radio's programming before it reaches the radio.

Run on every fleet export (the findings go into the export report) and on
its own with ``wasds150 fleet audit``. An *error* is a memory that is wrong on
the air; a *warning* needs a human to look.

Transmit, from the channel's service (:mod:`wasds150.radios.services`):

* ``transmit-blocked`` (error): an amateur, GMRS/FRS or MURS memory the
  operator may use and the radio can transmit on, programmed receive only.
  A DMR or D-STAR copy of a repeater another memory already keys is fine; a
  DMR memory with no talkgroup cannot be keyed and is a warning
  (``dmr-no-talkgroup``).
* ``transmit-unlicensed`` (error): transmit on anything else.
* ``repeater-offset`` (warning): an amateur pair whose split is not the
  band's usual one and that no coordination confirms.

Against WWARA's coordination records (:mod:`wasds150.plan.coordination`), for
analog amateur repeaters with transmit. Tones compare as ``103.5`` (CTCSS) or
``D172`` (DCS). WWARA coordinates western Washington only, so a record is
trusted over a memory's name only when that name places the memory where the
record is (the record's city is in it); otherwise the disagreement is a
warning - an eastern machine can share a western pair.

* ``coordination-input`` (error): the named call is coordinated on this
  output, but on another input.
* ``coordination-tone`` (error): the named call's access tone is not the one
  programmed, or a memory named for a coordinated machine's city carries
  another tone.
* ``coordination-call``: the input and tone belong to another coordinated
  call (error when the name places the memory at that machine), or the output
  is coordinated only to other calls (warning).
* ``coordination-expired`` (warning): every record for the named call lapsed.
* ``tone-unconfirmed`` (warning): no call in the name, and no coordinated
  machine on the pair uses the programmed tone.
* ``conflicting-copies`` (warning): one call on one output programmed more
  than one way, unless each way is one of that call's coordinations (one
  club can run two machines on a pair).

A curated channel whose note says ``shared pair`` is a second machine on a
coordinated pair (Carlsborg on W7FEL's Striped Peak pair) and is not checked
against the coordination. D-STAR memories are not checked against the
licensee call: their name is the repeater's D-STAR routing call.

:func:`audit_export` checks the written file as well: the TH-D75 blocks PTT
with an out-of-band split, CHIRP with ``Duplex=off`` and the Anytone CPS with
``PTT Prohibit``, so a memory the plan transmits on must carry none of them.
"""
from __future__ import annotations

import csv
import io
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from wasds150.plan.coordination import STATUS_EXPIRED, Coordination, CoordinationIndex
from wasds150.plan.resolve import ResolvedPlan
from wasds150.radios.bandplan import may_transmit
from wasds150.radios.services import AMATEUR, FRS, GMRS, MURS_SERVICE, service_for
from wasds150.radios.tones import TONE_CTCSS, TONE_DCS

ERROR = "error"
WARNING = "warning"

#: A US amateur call sign.
CALLSIGN = re.compile(r"\b(?:[KNW][A-Z]?|A[A-L])\d[A-Z]{1,3}\b")
#: The note that marks a second machine on a coordinated pair.
SHARED_PAIR = "shared pair"

#: Usual repeater splits by band (MHz), Pacific Northwest practice.
_STANDARD_SPLITS = (
    ((50.0, 54.0), (0.5, 1.0, 1.7)),
    ((144.0, 148.0), (0.6, 1.0)),
    ((222.0, 225.0), (1.6,)),
    ((420.0, 450.0), (5.0,)),
    ((902.0, 928.0), (12.0, 25.0)),
    ((1240.0, 1300.0), (12.0, 20.0)),
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    radio_id: str
    slot: int
    name: str
    freq_mhz: float
    detail: str
    source: str = ""
    #: The memory's mode as planned (FM, NFM, DV, ...), when known.
    mode: str = ""
    #: What to change, for the per-radio corrections table.
    correction: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def line(self) -> str:
        where = f"slot {self.slot} {self.name} {self.freq_mhz:.4f}" if self.slot else self.name
        source = f" ({self.source})" if self.source else ""
        fix = f" -> {self.correction}" if self.correction else ""
        return f"{self.severity.upper()} {self.code} [{self.radio_id}] {where}: {self.detail}{fix}{source}"


def _splits(freq: float) -> Tuple[float, ...]:
    for (low, high), splits in _STANDARD_SPLITS:
        if low <= freq <= high:
            return splits
    return ()


def _calls(label: str) -> Set[str]:
    return set(CALLSIGN.findall(label.upper()))


def _dcs(text: str) -> Optional[str]:
    digits = re.sub(r"\D", "", text or "")
    return f"D{int(digits):03d}" if digits else None


def _tone_key(channel) -> Optional[str]:
    """The access tone a memory transmits: ``103.5``, ``D172`` or ``None``."""
    tone = channel.tx_tone
    if tone is None:
        return None
    if tone.kind == TONE_CTCSS and tone.ctcss_hz is not None:
        return f"{tone.ctcss_hz:g}"
    if tone.kind == TONE_DCS and tone.dcs_code:
        return _dcs(tone.dcs_code)
    return None


def _record_tone(record: Coordination) -> Optional[str]:
    if record.ctcss_in is not None:
        return f"{record.ctcss_in:g}"
    return _dcs(record.dcs)


def _same_mhz(a: Optional[float], b: Optional[float]) -> bool:
    return a is not None and b is not None and abs(a - b) < 0.0005


def _places(label: str, record: Coordination) -> bool:
    """The memory's name puts it at the record's site: the first word of
    the record's city is in it."""
    words = [word for word in re.split(r"[^a-z]+", record.city.lower()) if len(word) >= 3]
    return bool(words) and words[0] in label.lower()


def _who(records: List[Coordination]) -> str:
    return ", ".join(sorted({f"{r.call} ({r.city})" for r in records}))


def audit_plan(
    radio_id: str, resolved: ResolvedPlan, coordination: Optional[CoordinationIndex] = None
) -> List[Finding]:
    plan, profile = resolved.plan, resolved.profile
    gmrs_ok = plan.gmrs_licensed or bool(plan.gmrs_call)
    findings: List[Finding] = []

    def add(severity: str, code: str, channel, detail: str) -> None:
        findings.append(Finding(severity, code, radio_id, channel.slot, channel.name, channel.rx_freq_mhz,
                                detail, channel.source))

    def licensed(freq: float) -> bool:
        service = service_for(freq)
        if service == AMATEUR:
            return bool(plan.license_class) and may_transmit(freq, plan.license_class)
        if service in (GMRS, FRS):
            return gmrs_ok
        return service == MURS_SERVICE

    keyed_outputs = {round(c.rx_freq_mhz, 4) for c in resolved.channels if c.transmit}
    copies: Dict[Tuple[float, str], Set[Tuple[float, Optional[str]]]] = defaultdict(set)
    copy_channels: Dict[Tuple[float, str], object] = {}

    for channel in resolved.channels:
        freq = channel.rx_freq_mhz
        mode = (channel.mode or "").upper()
        if channel.transmit:
            tx_at = channel.tx_freq_mhz if channel.tx_freq_mhz is not None else freq
            if not licensed(tx_at):
                add(ERROR, "transmit-unlicensed", channel, f"transmits on {tx_at:.4f}, outside the operator's licences")
        elif service_for(freq) is not None and licensed(freq) and profile.can_transmit(freq):
            if mode in ("DMR", "DV") and round(freq, 4) in keyed_outputs:
                pass  # another memory keys this repeater
            elif mode == "DMR":
                add(WARNING, "dmr-no-talkgroup", channel, "DMR memory with no talkgroup cannot be keyed; add a talkgroup")
            elif mode in ("NXDN", "AM", "WFM"):
                pass  # modes this project never transmits
            else:
                add(ERROR, "transmit-blocked", channel,
                    f"{service_for(freq)} memory the {profile.model} can transmit on is programmed receive only")

        if not (channel.transmit and channel.tx_freq_mhz is not None and service_for(freq) == AMATEUR):
            continue
        tx = channel.tx_freq_mhz
        records = coordination.on_output(freq) if coordination is not None else []
        paired = [r for r in records if _same_mhz(r.input_mhz, tx)]
        splits = _splits(freq)
        shift = abs(tx - freq)
        if splits and not paired and not any(abs(shift - s) < 0.0006 for s in splits):
            add(WARNING, "repeater-offset", channel,
                f"input {tx:.4f} is a {shift:.4f} MHz split, not the band's usual " + "/".join(f"{s:g}" for s in splits))
        if mode not in ("FM", "NFM") or SHARED_PAIR in (channel.comment or "").lower():
            continue
        calls = _calls(channel.label)
        tone = _tone_key(channel)
        shown = tone or "none"
        for call in calls:
            copies[(round(freq, 4), call)].add((round(tx, 4), tone))
            copy_channels[(round(freq, 4), call)] = channel
        if not records:
            continue
        # The live coordinated machines on this pair that use the programmed tone.
        by_tone = [r for r in paired if r.live and tone is not None and _record_tone(r) == tone]
        named = [r for r in records if r.call in calls]
        if named:
            named_paired = [r for r in named if r in paired]
            if not named_paired:
                inputs = sorted({f"{r.input_mhz:.4f}" for r in named if r.input_mhz is not None})
                if inputs:
                    add(ERROR, "coordination-input", channel,
                        f"programmed input {tx:.4f}; WWARA has {', '.join(sorted(calls))} on {', '.join(inputs)}")
                continue
            tones = {t for t in (_record_tone(r) for r in named_paired) if t is not None}
            if tones and tone not in tones:
                others = [r for r in by_tone if r.call not in calls]
                if others:
                    add(ERROR if any(_places(channel.label, r) for r in others) else WARNING, "coordination-call",
                        channel, f"named {', '.join(sorted(calls))}, but input {tx:.4f} with tone {shown} is {_who(others)}")
                else:
                    add(ERROR, "coordination-tone", channel,
                        f"access tone {shown}; WWARA's for {', '.join(sorted(calls))} is {', '.join(sorted(tones))}")
            if all(r.status == STATUS_EXPIRED for r in named):
                add(WARNING, "coordination-expired", channel,
                    "coordination lapsed " + ", ".join(sorted({r.expires for r in named})))
            continue
        live_toned = [r for r in paired if r.live and _record_tone(r) is not None]
        if calls:
            if by_tone:
                add(ERROR if any(_places(channel.label, r) for r in by_tone) else WARNING, "coordination-call",
                    channel, f"named {', '.join(sorted(calls))}, but input {tx:.4f} with tone {shown} is {_who(by_tone)}")
            elif any(r.live for r in records):
                add(WARNING, "coordination-call", channel,
                    f"{freq:.4f} is coordinated to {_who([r for r in records if r.live])}, not {', '.join(sorted(calls))}")
        elif live_toned and not by_tone:
            placed = [r for r in live_toned if _places(channel.label, r)]
            detail = (f"tone {shown} matches no coordinated machine on this pair: "
                      + ", ".join(sorted({f"{r.call} ({r.city}) {_record_tone(r)}" for r in live_toned})))
            add(ERROR if placed else WARNING, "coordination-tone" if placed else "tone-unconfirmed", channel, detail)

    for key, settings in sorted(copies.items()):
        if len(settings) < 2:
            continue
        freq, call = key
        mine = [r for r in (coordination.on_output(freq) if coordination is not None else []) if r.call == call and r.live]
        if mine and all(
            any(_same_mhz(r.input_mhz, tx) and _record_tone(r) in (None, tone) for r in mine)
            for tx, tone in settings
        ):
            continue  # every way it is programmed is one of that call's coordinations
        detail = "; ".join(
            f"input {tx:.4f} tone {tone or 'none'}" for tx, tone in sorted(settings, key=lambda s: (s[0], s[1] or ""))
        )
        add(WARNING, "conflicting-copies", copy_channels[key], f"{call} on {freq:.4f} is programmed more than one way: {detail}")
    return findings


def _keyed_by_name(resolved: ResolvedPlan) -> Dict[Tuple[str, float], object]:
    return {(c.name, round(c.rx_freq_mhz, 4)): c for c in resolved.channels if c.transmit}


def _float(text: Optional[str]) -> Optional[float]:
    try:
        return round(float((text or "").strip()), 4)
    except ValueError:
        return None


def audit_export(radio_id: str, resolved: ResolvedPlan, path: Path) -> List[Finding]:
    """Check the written file for transmit blocks the plan did not ask for."""
    path = Path(path)
    keyed = _keyed_by_name(resolved)
    blocked: List[Tuple[object, str]] = []
    if radio_id == "th-d75" and path.is_file():
        from wasds150.export.thd75_target import inspect_thd75

        for row in inspect_thd75(path.read_bytes()):
            channel = keyed.get((row["name"], round(row["rx_mhz"], 4)))
            if channel is not None and row["split"]:
                blocked.append((channel, "the .d75 memory carries the out-of-band PTT-inhibit split"))
    elif radio_id == "td-h9" and path.is_file():
        for row in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))):
            channel = keyed.get((row.get("Name", ""), _float(row.get("Frequency"))))
            if channel is not None and (row.get("Duplex") or "").strip().lower() == "off":
                blocked.append((channel, "the CHIRP row has Duplex=off"))
    elif radio_id == "at-d890uv" and (path / "Channel.CSV").is_file():
        text = (path / "Channel.CSV").read_bytes().decode("utf-8-sig", errors="replace")
        for row in csv.DictReader(io.StringIO(text)):
            channel = keyed.get((row.get("Channel Name", ""), _float(row.get("Receive Frequency"))))
            if channel is not None and (row.get("PTT Prohibit") or "").strip().lower() == "on":
                blocked.append((channel, "the CPS row has PTT Prohibit = On"))
    return [
        Finding(ERROR, "export-transmit-blocked", radio_id, channel.slot, channel.name, channel.rx_freq_mhz,
                detail, channel.source)
        for channel, detail in blocked
    ]


def summarize(findings: List[Finding]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for finding in findings:
        counts[f"{finding.severity}:{finding.code}"] += 1
    return dict(sorted(counts.items()))
