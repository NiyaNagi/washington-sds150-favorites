"""Checks across the whole fleet: each radio holds the right stations for its
capability, and every radio agrees with the others.

Run by ``wasds150 fleet audit`` after the per-radio checks
(:mod:`wasds150.plan.audit`), on every fleet plan and the SDS150's Favorites
Lists. The radios' capabilities are their profiles
(:mod:`wasds150.radios.registry`, rendered in docs/radio-capabilities.md).

* ``capability-violation`` (error): a memory outside the radio's receive
  coverage, in a mode the radio cannot use there, or keyed outside its
  transmit bands.
* ``dstar-as-analog`` (error): an FM memory of a machine that is D-STAR only,
  on a radio with D-STAR. The station belongs in its D-STAR memory.
* ``dstar-unsupported`` (error): a D-STAR machine on a radio without D-STAR,
  as a D-STAR memory or as an FM copy of one. It is left off such radios.
* ``dstar-name`` (error): a D-STAR memory not named for its routing call
  (``K7LWH C``), which is what the radio's DR screens show.
* ``dstar-missing`` (warning): a D-STAR-only machine within Near Me reach of
  home that a D-STAR radio has no D-STAR memory for.
* ``mixed-missing-dv`` (warning): a machine WWARA lists as mixed FM/D-Star
  that a D-STAR radio holds only as FM.
* ``station-mismatch`` (error): one repeater - output, input and call - keyed
  with different access tones on different radios.
* ``dstar-hint`` (warning, SDS150): a row whose source calls it D-STAR
  but that no D-STAR machine in the registry confirms.
* ``pinned-missing`` (error): a pinned Near Me station (KC7BAE 443.050,
  WW7PSR 146.960) missing from a radio's first scan group, from the TD-H9's
  memories (it has no groups), or from the SDS150's Near Me ham list.

A machine is D-STAR from the repeater registry's D-STAR records (WWARA and
DSTARInfo, merged) and WWARA's own "D-Star" mode. It is D-STAR *only* unless
WWARA lists it as mixed ("FM/D-Star") or WWARA coordinates an analog machine
on the same pair at the same site - then an FM memory is right as well, and
the D-STAR radios carry both.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from wasds150.models.catalog import Catalog, FavoritesList
from wasds150.plan.audit import ERROR, WARNING, Finding, _calls, _tone_key
from wasds150.plan.coordination import CoordinationIndex
from wasds150.plan.resolve import PlannedChannel, ResolvedPlan
from wasds150.plan.scanning import group_members, is_pinned
from wasds150.radios.profile import RadioProfile
from wasds150.util.geo import haversine_miles

#: Two copies closer than this are one site.
SAME_SITE_MILES = 25.0
#: A copy with a position this far from a machine is another machine.
OTHER_MACHINE_MILES = 60.0
#: How far from home a D-STAR machine must be missed before it is reported.
NEAR_HOME_MILES = 35.0
_DSTAR_HINT = re.compile(r"D-?STAR", re.IGNORECASE)
_MIXED = re.compile(r"\bN?FM/D-?Star\b", re.IGNORECASE)
_TOLERANCE = 0.0006


@dataclass(frozen=True)
class DStarMachine:
    call: str
    module: str
    output: float
    input: Optional[float]
    lat: Optional[float]
    lon: Optional[float]
    avoid: bool
    #: WWARA lists it as mixed FM/D-Star.
    mixed: bool
    #: An analog machine on this pair at this site: coordinated by WWARA, or -
    #: for a machine WWARA does not coordinate - listed as FM under the same
    #: call (DSTARInfo and RepeaterBook disagree; both memories are kept).
    analog_here: bool
    #: WWARA coordinates this call on this pair.
    wwara: bool = False

    @property
    def routing(self) -> str:
        return f"{self.call:<7}{self.module}"

    @property
    def analog_ok(self) -> bool:
        return self.mixed or self.analog_here


def _same(a: float, b: float) -> bool:
    return abs(a - b) < _TOLERANCE


def _compact(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (text or "").upper())


def _miles(lat1, lon1, lat2, lon2) -> Optional[float]:
    if None in (lat1, lon1, lat2, lon2):
        return None
    return haversine_miles(lat1, lon1, lat2, lon2)


def wwara_mode(notes: str) -> str:
    """WWARA's mode for a PSHAM01 copy - the third field of its note
    (``input 448.9000; +5.0000 MHz; FM/D-Star; ...``) - or ""."""
    parts = (notes or "").split("; ")
    return parts[2].strip() if len(parts) > 2 and parts[0].startswith("input") else ""


def _pair(a, b) -> bool:
    if not _same(a.freq_mhz, b.freq_mhz):
        return False
    return a.tx_freq_mhz is None or b.tx_freq_mhz is None or _same(a.tx_freq_mhz, b.tx_freq_mhz)


def dstar_machines(catalog: Catalog) -> List[DStarMachine]:
    """Every D-STAR machine the registry holds in Washington, with whether an
    FM memory on its pair is also right."""
    wwara: List = []  # WWARA copies from PSHAM01
    registry: List = []
    analog: List = []  # the registry's analog records in Washington
    for favorite in catalog.favorites:
        key = favorite.favorite_key.upper()
        for system in favorite.systems:
            for department in system.departments:
                for channel in department.channels:
                    if channel.freq_mhz is None:
                        continue
                    if key == "PSHAM01":
                        wwara.append(channel)
                    elif key == "HAMREG" and department.label.startswith("Washington - D-STAR"):
                        if (channel.mode or "").upper() == "DV" and channel.dv_rpt1.strip():
                            registry.append(channel)
                    elif key == "HAMREG" and department.label.startswith("Washington - Analog"):
                        analog.append(channel)
    machines: List[DStarMachine] = []
    for c in registry:
        call, module = c.dv_rpt1[:7].strip().upper(), c.dv_rpt1[7:8].strip().upper()
        mixed = analog_here = coordinated = False
        for w in wwara:
            if not _pair(w, c):
                continue
            mode = wwara_mode(w.notes or "")
            distance = _miles(w.lat, w.lon, c.lat, c.lon)
            if call in _calls(w.label or ""):
                coordinated = True
                if _MIXED.fullmatch(mode or ""):
                    mixed = True
            if re.match(r"N?FM", mode) and not re.fullmatch(r"D-?Star", mode, re.IGNORECASE) \
                    and not _MIXED.fullmatch(mode) and distance is not None and distance <= SAME_SITE_MILES:
                analog_here = True
        if not coordinated:
            # DSTARInfo's machine; an FM listing of the same call is the other
            # source's view of it, and both memories are kept.
            for a in analog:
                distance = _miles(a.lat, a.lon, c.lat, c.lon)
                if _pair(a, c) and call in _calls(a.label or "") and (distance is None or distance <= OTHER_MACHINE_MILES):
                    analog_here = True
        machines.append(DStarMachine(call, module, c.freq_mhz, c.tx_freq_mhz, c.lat, c.lon, c.avoid, mixed,
                                     analog_here, coordinated))
    return machines


def mixed_wwara(catalog: Catalog) -> List[Tuple[str, float, Optional[float]]]:
    """WWARA's mixed FM/D-Star machines: (call, output, input)."""
    found = []
    for favorite in catalog.favorites:
        if favorite.favorite_key.upper() != "PSHAM01":
            continue
        for system in favorite.systems:
            for department in system.departments:
                for c in department.channels:
                    if c.freq_mhz is not None and _MIXED.fullmatch(wwara_mode(c.notes or "")):
                        calls = _calls(c.label or "")
                        if calls:
                            found.append((sorted(calls)[0], c.freq_mhz, c.tx_freq_mhz))
    return found


class _SourceIndex:
    """The catalog copy a planned memory came from, for its label and notes."""

    def __init__(self, catalog: Catalog) -> None:
        self._rows: Dict[Tuple[str, float], List] = defaultdict(list)
        for favorite in catalog.favorites:
            for system in favorite.systems:
                for department in system.departments:
                    for c in department.channels:
                        if c.freq_mhz is not None:
                            self._rows[(f"{favorite.favorite_key}/{department.label}", round(c.freq_mhz, 4))].append(c)

    def text(self, source: str, freq: float) -> str:
        rows = self._rows.get((source, round(freq, 4)), [])
        return " ".join(f"{c.label} {c.notes}" for c in rows)


def _match(machines: Sequence[DStarMachine], rx: float, tx: Optional[float], label: str, text: str,
           lat: Optional[float], lon: Optional[float]) -> Optional[DStarMachine]:
    """The D-STAR machine this memory is a copy of, if it is one.

    Named for the machine's call, it is that machine unless it sits
    elsewhere. Named for another call, it is another machine unless its
    source says D-STAR. Unnamed, it is the machine at its site, or - with no
    site - the machine its source says is D-STAR."""
    calls = _calls(label)
    hinted = bool(_DSTAR_HINT.search(text)) and not _MIXED.search(text)
    for m in machines:
        if not _same(m.output, rx):
            continue
        if tx is not None and m.input is not None and abs(tx - rx) > 0.01 and not _same(m.input, tx):
            continue
        named = m.call in calls or m.call in _calls(text)
        distance = _miles(lat, lon, m.lat, m.lon)
        if named:
            if distance is None or distance <= OTHER_MACHINE_MILES:
                return m
            continue
        if calls and not hinted:
            continue
        if distance is not None:
            if distance <= SAME_SITE_MILES:
                return m
            continue
        if hinted:
            return m
    return None


def _finding(severity, code, radio_id, ch: PlannedChannel, detail, correction) -> Finding:
    return Finding(severity, code, radio_id, ch.slot, ch.name, ch.rx_freq_mhz, detail, ch.source,
                   mode=ch.mode or "", correction=correction)


def audit_radio(radio_id: str, resolved: ResolvedPlan, machines: Sequence[DStarMachine],
                mixed: Sequence[Tuple[str, float, Optional[float]]], sources: _SourceIndex,
                home: Optional[Tuple[float, float]] = None) -> List[Finding]:
    profile = resolved.profile
    dv_radio = profile.supports_mode("DV")
    findings: List[Finding] = []
    for ch in resolved.channels:
        mode = (ch.mode or "").upper()
        rx, tx = ch.rx_freq_mhz, (ch.tx_freq_mhz if ch.transmit else ch.input_freq_mhz)
        # Capability.
        if not profile.can_receive(rx):
            findings.append(_finding(ERROR, "capability-violation", radio_id, ch,
                                     f"{profile.model} does not receive {rx:.4f} MHz", "remove the memory"))
        elif mode and not profile.supports_mode(mode, rx):
            findings.append(_finding(ERROR, "capability-violation", radio_id, ch,
                                     f"{profile.model} cannot use {mode} at {rx:.4f} MHz", "remove the memory"))
        if ch.transmit and not profile.can_transmit(ch.tx_freq_mhz if ch.tx_freq_mhz is not None else rx):
            findings.append(_finding(ERROR, "capability-violation", radio_id, ch,
                                     f"keyed outside {profile.model}'s transmit bands", "make it receive only"))
        # D-STAR.
        if mode == "DV":
            call, module = ch.dv_rpt1[:7].strip().upper(), ch.dv_rpt1[7:8].strip().upper()
            if not dv_radio:
                findings.append(_finding(ERROR, "dstar-unsupported", radio_id, ch,
                                         f"{profile.model} has no D-STAR", "remove the memory"))
            elif call and not _compact(ch.name).startswith(_compact(call) + module):
                findings.append(_finding(ERROR, "dstar-name", radio_id, ch,
                                         f"D-STAR memory for {call} {module} is named {ch.name!r}",
                                         f"name it for its routing call: {call} {module}"))
            continue
        if mode not in ("FM", "NFM", "AUTO", ""):
            continue
        text = sources.text(ch.source, rx)
        machine = _match(machines, rx, tx, ch.label or ch.name, text, ch.lat, ch.lon)
        if machine is None or machine.analog_ok:
            continue
        what = f"{machine.call} {machine.module} is D-STAR only" + (" (coordination lapsed)" if machine.avoid else "")
        if dv_radio:
            findings.append(_finding(ERROR, "dstar-as-analog", radio_id, ch, f"{what}; programmed {mode or 'FM'}",
                                     f"remove the FM copy; keep a D-STAR memory {machine.call} {machine.module}"))
        else:
            findings.append(_finding(ERROR, "dstar-unsupported", radio_id, ch,
                                     f"{what}; {profile.model} has no D-STAR", "remove the memory"))
    if dv_radio:
        routed = {c.dv_rpt1.upper() for c in resolved.channels if (c.mode or "").upper() == "DV"}
        dv_outputs = [c.rx_freq_mhz for c in resolved.channels if (c.mode or "").upper() == "DV"]
        for m in machines:
            if m.avoid or m.routing.upper() in routed or m.analog_ok or home is None:
                continue
            if not (profile.can_receive(m.output) and profile.supports_mode("DV", m.output)):
                continue
            distance = _miles(home[0], home[1], m.lat, m.lon)
            if distance is not None and distance <= NEAR_HOME_MILES:
                findings.append(Finding(WARNING, "dstar-missing", radio_id, 0, f"{m.call} {m.module}", m.output,
                                        f"D-STAR machine {distance:.0f} mi from home has no D-STAR memory",
                                        "HAMREG", mode="DV",
                                        correction=f"add D-STAR memory {m.call} {m.module} {m.output:.4f}"))
        for call, output, _input in mixed:
            if any(_same(output, f) for f in dv_outputs) or not profile.can_receive(output):
                continue
            module = next((m.module for m in machines if m.call == call and _same(m.output, output)), "")
            findings.append(Finding(WARNING, "mixed-missing-dv", radio_id, 0, call, output,
                                    "WWARA lists FM/D-Star; only the FM side is programmed", "PSHAM01", mode="FM",
                                    correction=(f"add D-STAR memory {call} {module}" if module
                                                else "add a D-STAR memory once its module is known")))
    # The pinned Near Me stations.
    groups = resolved.plan.scan_groups
    if groups:
        group = groups[0]
        members = group_members(group, resolved.channels)
        for freq, call in group.pinned:
            if not any(is_pinned(c, ((freq, call),)) for c in members):
                findings.append(Finding(ERROR, "pinned-missing", radio_id, 0, call, freq,
                                        f"{call} {freq:.3f} is not in {group.name}", "",
                                        correction=f"pin {call} {freq:.3f} into {group.name}"))
    else:
        from wasds150.plans.template import NEAR_ME_PINNED

        for freq, call in NEAR_ME_PINNED:
            if not any(is_pinned(c, ((freq, call),)) for c in resolved.channels):
                findings.append(Finding(ERROR, "pinned-missing", radio_id, 0, call, freq,
                                        f"{call} {freq:.3f} is not programmed", "",
                                        correction=f"program {call} {freq:.3f}"))
    return findings


def audit_across(resolved_by_radio: Mapping[str, ResolvedPlan], coordination: Optional[CoordinationIndex]) -> List[Finding]:
    """``station-mismatch``: one keyed repeater with different access tones on
    different radios. WWARA's tone decides when it coordinates the call on the
    pair; otherwise the tone most radios carry."""
    tones: Dict[Tuple[float, float, str], Dict[str, List[PlannedChannel]]] = defaultdict(lambda: defaultdict(list))
    for radio_id, resolved in resolved_by_radio.items():
        for ch in resolved.channels:
            if not ch.transmit or ch.tx_freq_mhz is None or (ch.mode or "").upper() not in ("FM", "NFM"):
                continue
            for call in _calls(ch.label or ch.name):
                tones[(round(ch.rx_freq_mhz, 4), round(ch.tx_freq_mhz, 4), call)][radio_id].append(ch)
    findings: List[Finding] = []
    for (rx, tx, call), by_radio in tones.items():
        if len(by_radio) < 2:
            continue
        seen = {radio: {_tone_key(c) for c in chans} for radio, chans in by_radio.items()}
        values = set().union(*seen.values())
        if len(values) < 2:
            continue
        coordinated = set()
        if coordination is not None:
            for record in coordination.on_output(rx):
                if record.call == call and record.input_mhz is not None and _same(record.input_mhz, tx):
                    coordinated.add(f"{record.ctcss_in:g}" if record.ctcss_in is not None else None)
        if coordinated:
            right = coordinated
        else:
            votes = Counter(t for radio_tones in seen.values() for t in radio_tones)
            right = {votes.most_common(1)[0][0]}
        for radio, chans in by_radio.items():
            for ch in chans:
                tone = _tone_key(ch)
                if tone in right:
                    continue
                others = ", ".join(f"{r} {'/'.join(sorted(str(t) for t in ts))}" for r, ts in sorted(seen.items()) if r != radio)
                findings.append(_finding(ERROR, "station-mismatch", radio, ch,
                                         f"{call} keyed with tone {tone or 'none'}; other radios: {others}",
                                         f"set access tone {'/'.join(sorted(str(t) for t in right))}"))
    return findings


def audit_scanner(favorites: Iterable[FavoritesList], machines: Sequence[DStarMachine]) -> List[Finding]:
    """The SDS150: no D-STAR machines (it cannot decode them), and the pinned
    stations in its Near Me ham list."""
    from wasds150.plans.template import NEAR_ME_PINNED

    findings: List[Finding] = []
    near_me_ham = []
    for favorite in favorites:
        for system in favorite.systems:
            for department in system.departments:
                for c in department.channels:
                    if c.freq_mhz is None or c.tgid is not None:
                        continue
                    mode = (c.mode or "").upper()
                    if favorite.favorite_key == "NM-HAM":
                        near_me_ham.append(c)
                    where = f"{favorite.favorite_key}/{department.label}"
                    hinted = mode == "AUTO" and bool(_DSTAR_HINT.search(f"{c.label} {c.notes}")) \
                        and not _MIXED.search(c.notes or "")
                    if mode == "DV":
                        severity, detail = ERROR, "the SDS150 cannot decode D-STAR"
                    elif mode in ("FM", "NFM", "AUTO", ""):
                        found = _match(machines, c.freq_mhz, c.tx_freq_mhz, c.label or "", f"{c.label} {c.notes}",
                                       c.lat, c.lon)
                        if found is not None and not found.analog_ok:
                            severity = ERROR
                            detail = f"{found.call} {found.module} is D-STAR only; the SDS150 cannot decode it"
                        elif found is None and hinted:
                            severity, detail = WARNING, "its source lists it as D-STAR; no D-STAR machine confirms it"
                        else:
                            continue
                    else:
                        continue
                    findings.append(Finding(severity, "dstar-unsupported" if severity == ERROR else "dstar-hint",
                                            "sds150", 0, c.label, c.freq_mhz, detail, where, mode=mode,
                                            correction="leave it off the scanner" if severity == ERROR
                                            else "check the source; leave it off if it is D-STAR"))
    for freq, call in NEAR_ME_PINNED:
        if not any(abs(c.freq_mhz - freq) < _TOLERANCE and call in (c.label or "").upper()
                   and (c.mode or "").upper() in ("FM", "NFM") for c in near_me_ham):
            findings.append(Finding(ERROR, "pinned-missing", "sds150", 0, call, freq,
                                    f"{call} {freq:.3f} is not in NM Ham", "NM-HAM",
                                    correction=f"add {call} {freq:.3f} to NM Ham"))
    return findings
