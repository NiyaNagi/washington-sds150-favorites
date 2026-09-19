"""HAMREG: the amateur repeater registry - one record per machine.

Every source in the catalog says something about the same repeaters: WWARA
coordinates western Washington (call, pair, access tone, position), IACC the
east, DSTARInfo lists D-STAR modules with approximate positions, its DR-radio
download carries RepeaterBook's FM repeaters with approximate positions, and
the RadioReference county lists and the FTX-1 import carry descriptions. Radio
plans used to pick from each list separately, so what a repeater was called
and where it sat depended on which list a block happened to read.

The registry merges them into one record per machine. Coordination decides
identity:

* **Coordinator records are machines.** Two WWARA or IACC records are one
  only when call, input and access tone all agree (the same record in two
  lists). Two machines sharing a call and an output in different places stay
  two.
* **Everything else attaches to them.** A copy carrying the same call joins
  that machine within 120 miles (RepeaterBook's approximate positions can be
  that far off), whatever input or tone it wrote. A copy with another call on
  a coordinated pair - the same output and input - within 60 miles is the
  same machine listed under an owner's, trustee's or club's call (N6OBY for
  KJ7JNK Redmond), so it joins the coordinated machine, the one whose tone it
  matches when two share the pair. A copy on a coordinated pair that cannot be
  placed on one machine is left out rather than becoming a second, conflicting
  one. A copy on no coordinated pair stands alone (an uncoordinated
  repeater), or joins the one uncalled machine on its pair.
* **Fields.** Each field comes from the best source that has it: WWARA, then
  IACC and the operator-published lists, DSTARInfo, RadioReference,
  RepeaterBook (through DSTARInfo), the FTX-1 import. A record is named by a
  call only a coordinator, an operator-published list or DSTARInfo gives it. A
  position comes only from a source that publishes the repeater's own: WWARA,
  then DSTARInfo's and RepeaterBook's approximate positions.
* **Provenance.** Each record's note names the sources it merged and where its
  position came from.

Seattle ACS channels are not merged: they are the ACS plan's own designators
and tones, programmed by their own block.

Departments are ``<State> - <band or mode>`` ("Washington - Analog 2 Meter",
"Oregon - D-STAR"), fenced around their stations. Radio plans and the Near
Me lists read the Washington departments; the rest are there to pick from.
The registry is rebuilt whenever a catalog is loaded or saved.
"""
from __future__ import annotations

import math
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from wasds150.models.catalog import ORIGIN_LOCAL, Catalog, Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.radios.services import AMATEUR, service_for
from wasds150.radios.tones import TONE_CTCSS, TONE_DCS, parse_tone
from wasds150.util.geo import haversine_miles
from wasds150.util.hashing import stable_id

REGISTRY_KEY = "HAMREG"
DSTARINFO_KEY = "DSTARINFO"
DSTARFM_KEY = "DSTARFM"
#: The state whose departments radio plans and the Near Me lists read.
HOME_STATE = "Washington"
#: The note prefix the DSTARInfo lists use for a repeater's state or province.
STATE_NOTE = "state: "

WWARA = "WWARA"
IACC = "IACC"
OPERATOR = "operator-published"
DSTARINFO = "DSTARInfo"
RADIOREFERENCE = "RadioReference"
REPEATERBOOK = "RepeaterBook via DSTARInfo"
FTX1 = "FTX-1 import"
#: Merge precedence, best first.
RANK: Dict[str, int] = {WWARA: 0, IACC: 1, OPERATOR: 1, DSTARINFO: 2, RADIOREFERENCE: 3, REPEATERBOOK: 4, FTX1: 5}
COORDINATORS = (WWARA, IACC)
#: Sources whose call names a record.
NAMING = (WWARA, IACC, OPERATOR, DSTARINFO)
#: Sources that publish a repeater's own position (not a county centre).
POSITIONED = (WWARA, DSTARINFO, REPEATERBOOK)
SAME_PLACE_MILES = 60.0
SAME_CALL_MILES = 120.0
#: Records farther from home than the FM download reaches are left out.
REACH_MILES = 750.0

_CALL = re.compile(r"\b((?:[AKNW][A-Z]?|A[A-L]|V[A-GEOY])\d[A-Z]{1,3})\b")
_RR_CALL = re.compile(r"\bcallsign: ([A-Z0-9]+)")
#: RadioReference's alpha tag, which starts with the repeater's own call.
_ALPHA_CALL = re.compile(r"\balpha: ((?:[AKNW][A-Z]?|A[A-L]|V[A-GEOY])\d[A-Z]{1,3})\b", re.IGNORECASE)
_INPUT_TOLERANCE_MHZ = 0.0015
_BANDS = (
    (50.0, 54.0, "Analog 6 Meter"), (144.0, 148.0, "Analog 2 Meter"), (219.0, 225.0, "Analog 1.25 Meter"),
    (420.0, 450.0, "Analog 70 Centimeter"), (902.0, 928.0, "Analog 33 Centimeter"), (1240.0, 1300.0, "Analog 23 Centimeter"),
)
_MODULES = ((144.0, 148.0, "C"), (420.0, 450.0, "B"), (1240.0, 1300.0, "A"))
_IACC_PLACE = re.compile(r"\(([^,()]+), ([^()]+?) Co\.\)")
#: WWARA's mode for a machine that repeats analog as well as a digital mode.
_MIXED = re.compile(r"\b(N?FM)/(?:P25|DMR|NXDN)\b")
#: WWARA's mode for a machine that repeats analog as well as D-STAR: both
#: sides are programmed, the analog one everywhere and the D-STAR one on the
#: radios that have it.
_MIXED_DSTAR = re.compile(r"\bN?FM/D-?Star\b", re.IGNORECASE)
_DROP = object()


@dataclass
class _Copy:
    source: str
    favorite_key: str
    department: Department
    channel: Channel
    family: str
    call: str
    module: str
    state: str

    @property
    def rank(self) -> int:
        return RANK[self.source]

    @property
    def located(self) -> bool:
        return self.channel.lat is not None and self.channel.lon is not None

    @property
    def access(self) -> str:
        tone = parse_tone(self.channel.tx_tone or self.channel.tone or "")
        if tone.kind == TONE_CTCSS and tone.ctcss_hz:
            return f"{tone.ctcss_hz:g}"
        if tone.kind == TONE_DCS and tone.dcs_code:
            return f"D{tone.dcs_code}"
        return ""

    @property
    def city(self) -> str:
        label = self.channel.label or ""
        if self.source == IACC:
            found = _IACC_PLACE.search(label)
            return found.group(1).strip() if found else ""
        return label.split(" - ", 1)[1].strip() if " - " in label and self.source in (WWARA, DSTARINFO, REPEATERBOOK) else ""

    @property
    def county(self) -> str:
        if self.source == IACC:
            found = _IACC_PLACE.search(self.channel.label or "")
            return found.group(2).strip().upper() if found else ""
        return self.favorite_key[4:].replace("-", " ") if self.favorite_key.startswith("RRC-") else ""


def _source_of(key: str, system: System) -> Optional[str]:
    from wasds150.catalog.puget_ham import WWARA_SYSTEM_ID
    from wasds150.catalog.wwara_coverage import COVERAGE_SYSTEM_LABEL

    if key == "PSHAM01":
        return WWARA if system.id == WWARA_SYSTEM_ID else OPERATOR
    if key == "PSHAM02":
        return WWARA
    if key == "FL60":
        return IACC if system.id == stable_id("fl60:coordination", kind="system") else None
    if key == "OZ01":
        return OPERATOR
    if key.startswith("RRC-"):
        return None if system.label == COVERAGE_SYSTEM_LABEL else RADIOREFERENCE
    if key == "FTX01":
        return FTX1
    if key == DSTARINFO_KEY:
        return DSTARINFO
    if key == DSTARFM_KEY:
        return REPEATERBOOK
    return None


def _family(channel: Channel) -> Optional[str]:
    mode = (channel.mode or "").upper()
    if mode == "DV":
        return "DV"
    if mode in ("P25", "NXDN", "DMR"):
        return mode
    if mode == "AUTO":
        return "DV" if re.search(r"D-?Star", channel.notes or "", re.IGNORECASE) else None
    if mode in ("", "FM", "NFM", "FMN"):
        return "FM"
    return None


def _band_value(frequency: float, table) -> str:
    return next((value for low, high, value in table if low <= frequency <= high), "")


def _copies(catalog: Catalog) -> Iterable[_Copy]:
    for favorite in catalog.favorites:
        key = favorite.favorite_key.upper()
        for system in favorite.systems:
            source = _source_of(key, system)
            if source is None:
                continue
            for department in system.departments:
                for channel in department.channels:
                    freq = channel.freq_mhz
                    if freq is None or channel.tgid is not None or service_for(freq) != AMATEUR:
                        continue
                    family = _family(channel)
                    tx = channel.tx_freq_mhz
                    if family is None or tx is None or abs(tx - freq) < 0.01:
                        continue  # not a repeater: simplex, a talkgroup, or a mode no radio here keys
                    if family == "DMR" and source not in COORDINATORS:
                        continue  # DMR repeaters are the talkgroup lists'; a coordinated one only anchors its pair
                    label = channel.label or ""
                    if family == "DV" and channel.dv_rpt1.strip():
                        call, module = channel.dv_rpt1[:7].strip().upper(), channel.dv_rpt1[7:8].strip().upper()
                    else:
                        # RadioReference's "alpha" is the repeater's own tag
                        # ("KF7BFS DSTAR"); its "callsign" is the licensee, who
                        # is often somebody else, so the alpha is read first.
                        found = (
                            (_ALPHA_CALL.search(channel.notes or "") if family == "DV" else None)
                            or _CALL.search(label.upper())
                            or _RR_CALL.search(channel.notes or "")
                        )
                        call, module = (found.group(1).upper() if found else ""), ""
                    if family == "DV" and not module:
                        module = _band_value(freq, _MODULES)
                    state = next(
                        (part[len(STATE_NOTE):].strip() for part in (channel.notes or "").split("; ") if part.startswith(STATE_NOTE)),
                        HOME_STATE,
                    )
                    yield _Copy(source, key, department, channel, family, call, module, state)


def _distance(machine: List[_Copy], copy: _Copy) -> Optional[float]:
    if not copy.located:
        return None
    miles = [
        haversine_miles(c.channel.lat, c.channel.lon, copy.channel.lat, copy.channel.lon) for c in machine if c.located
    ]
    return min(miles) if miles else None


def _tone_conflict(machine: List[_Copy], copy: _Copy) -> bool:
    tones = {c.access for c in machine if c.access}
    return bool(copy.access and tones and copy.access not in tones)


def _same_input(machine: List[_Copy], copy: _Copy) -> bool:
    return any(abs(c.channel.tx_freq_mhz - copy.channel.tx_freq_mhz) <= _INPUT_TOLERANCE_MHZ for c in machine)


def _within(machine: List[_Copy], copy: _Copy, miles: float) -> bool:
    distance = _distance(machine, copy)
    return distance is None or distance <= miles


def _nearest(machines: List[List[_Copy]], copy: _Copy) -> Optional[List[_Copy]]:
    if len(machines) == 1:
        return machines[0]
    placed = [(d, m) for m in machines for d in (_distance(m, copy),) if d is not None]
    return min(placed, key=lambda item: item[0])[1] if placed else None


def _first_word(text: str) -> str:
    return next((word for word in re.split(r"[^a-z]+", text.lower()) if word), "")


def _here(machine: List[_Copy], copy: _Copy) -> bool:
    """Whether ``copy`` sits where the coordinated ``machine`` does."""
    distance = _distance(machine, copy)
    if distance is not None:
        # The same pair and tone is one machine a little farther out: a
        # listing's position can be a degree off (W7EOC's Neilton at 47.39).
        same_tone = bool(copy.access) and copy.access in {c.access for c in machine}
        return distance <= (SAME_CALL_MILES if same_tone else SAME_PLACE_MILES)
    if not copy.located and any(c.located for c in machine):
        return True  # a county list's copy of a placed machine
    # Neither placed against the other (IACC publishes no positions): the
    # county or the city has to agree.
    return any(
        (copy.county and c.county == copy.county) or (copy.city and c.city and _first_word(copy.city) == _first_word(c.city))
        for c in machine
    )


def _target(found: List[List[_Copy]], copy: _Copy):
    """The machine ``copy`` belongs to, ``None`` for a new machine, or
    :data:`_DROP` for a copy on a coordinated pair that fits no one machine."""
    if copy.source in COORDINATORS:
        return next((
            m for m in found if any(
                c.source in COORDINATORS and c.family == copy.family and c.call == copy.call and c.access == copy.access
                and abs(c.channel.tx_freq_mhz - copy.channel.tx_freq_mhz) <= _INPUT_TOLERANCE_MHZ
                for c in m
            )
        ), None)
    # A D-STAR copy is only ever the D-STAR machine: a repeater WWARA lists as
    # mixed FM/D-Star is one machine with two sides, and each side is its own
    # record. An analog copy, finding no analog machine, joins the D-STAR one -
    # a county list's FM row for a D-STAR-only repeater is that repeater.
    def usable(machines: List[List[_Copy]]) -> List[List[_Copy]]:
        same = [m for m in machines if m[0].family == copy.family]
        return same if copy.family == "DV" else (same or machines)

    if copy.call:
        same_call = usable([
            m for m in found
            if copy.call in {c.call for c in m if c.call} and _within(m, copy, SAME_CALL_MILES)
        ])
        if same_call:
            pool = [m for m in same_call if not _tone_conflict(m, copy)] or same_call
            return _nearest(pool, copy) or pool[0]
    coordinated = usable([
        m for m in found if any(c.source in COORDINATORS for c in m) and _same_input(m, copy) and _here(m, copy)
    ])
    if coordinated:
        agreeing = [m for m in coordinated if not _tone_conflict(m, copy)]
        # A placed copy nearby is that machine whatever tone it wrote; an
        # unplaced one with another tone may be a different machine elsewhere.
        pool = agreeing or (coordinated if copy.located else [])
        target = _nearest(pool, copy) if pool else None
        return target if target is not None else _DROP
    uncalled = usable([
        m for m in found
        if _same_input(m, copy) and _within(m, copy, SAME_PLACE_MILES)
        and not any(c.call for c in m) and not _tone_conflict(m, copy)
    ])
    return uncalled[0] if len(uncalled) == 1 else None


def _machines(copies: Iterable[_Copy]) -> List[List[_Copy]]:
    groups: "OrderedDict[tuple, List[_Copy]]" = OrderedDict()
    for copy in sorted(copies, key=lambda c: (c.rank, c.favorite_key, c.channel.freq_mhz)):
        # Every mode on an output is one group: WWARA lists a mixed FM/P25
        # machine as P25 and RepeaterBook the same machine as FM, and a county
        # list's FM row for a D-STAR repeater has to meet that repeater.
        groups.setdefault(("RPT", round(copy.channel.freq_mhz, 4)), []).append(copy)
    machines: List[List[_Copy]] = []
    for group in groups.values():
        found: List[List[_Copy]] = []
        for copy in group:
            target = _target(found, copy)
            if target is _DROP:
                continue
            if target is None:
                found.append([copy])
            else:
                target.append(copy)
        machines.extend(found)
    return machines


def _valid_tone(tone: str) -> str:
    from wasds150.hpe.validation import tone_is_valid

    return tone if tone and tone_is_valid(tone) else ""


def _analog(tone: str) -> str:
    kind = parse_tone(tone or "").kind
    return tone if kind in (TONE_CTCSS, TONE_DCS) else ""


def _record(machine: List[_Copy]) -> Optional[Tuple[str, str, Channel]]:
    best = sorted(machine, key=lambda c: c.rank)
    lead = best[0]
    mixed = _MIXED.search(lead.channel.notes or "") if lead.source in COORDINATORS and lead.family != "FM" else None
    family = "FM" if mixed else lead.family
    if family == "DMR":
        return None  # a DMR-only machine: the talkgroup lists program it

    def first(test):
        return next((c for c in best if test(c)), None)

    call = next((c.call for c in best if c.call and c.source in NAMING), "")
    city = next((c.city for c in best if c.city and c.source in NAMING), "") or next((c.city for c in best if c.city), "")
    module = lead.module if lead.family == "DV" else ""
    toned = first(lambda c: c.access)
    position = first(lambda c: c.located and c.source in POSITIONED)
    noted = first(lambda c: c.source == OPERATOR and c.channel.notes) or first(lambda c: c.source == WWARA and c.channel.notes)
    state = HOME_STATE if any(c.source in COORDINATORS for c in best) else next(
        (c.state for c in best if c.state != HOME_STATE), HOME_STATE
    )
    if family == "FM":
        # A mixed machine's analog side, in WWARA's bandwidth; else the best copy's.
        mode = mixed.group(1) if mixed else next(
            ((c.channel.mode or "").upper() for c in best if (c.channel.mode or "").upper() in ("FM", "NFM")), "FM"
        )
        group = _band_value(lead.channel.freq_mhz, _BANDS) or "Analog Other"
    else:
        mode = lead.family
        group = {"DV": "D-STAR", "P25": "P25 Digital", "NXDN": "NXDN Digital"}[lead.family]
    name = f"{call} {module}".strip() if call and lead.family == "DV" else call
    label = f"{name} - {city}" if name and city else (name or lead.channel.label)
    wwara = [c for c in best if c.source == WWARA]
    avoid = any("coordination expired" in (c.channel.notes or "") or c.department.label.endswith("Link Frequencies") for c in wwara)
    pending = any("coordination pending" in (c.channel.notes or "") for c in wwara)
    sources = list(OrderedDict.fromkeys(c.source for c in best))
    where = (
        f"position: {position.source}" + ("" if position.source == WWARA else " (approximate)")
        if position is not None else "position: none published"
    )
    notes = "; ".join(part for part in (
        noted.channel.notes if noted is not None else "",
        "coordination pending" if pending and (noted is None or "coordination pending" not in noted.channel.notes) else "",
        f"registry: {', '.join(sources)}",
        where,
    ) if part)
    if family == "FM":
        # Analog tones only: a mixed machine's digital copy carries its NAC or colour code in ``tone``.
        tone = _valid_tone(_analog(toned.channel.tone) or _analog(toned.channel.tx_tone)) if toned is not None else ""
        tx_tone = _valid_tone(_analog(toned.channel.tx_tone) or _analog(toned.channel.tone)) if toned is not None else ""
    else:
        tone, tx_tone = _valid_tone(lead.channel.tone), ""
    ran = next((c.channel.nxdn_ran for c in best if c.channel.nxdn_ran is not None), None) if family == "NXDN" else None
    channel = Channel(
        id=stable_id(f"hamreg:{family}:{name or lead.channel.label}:{lead.channel.freq_mhz:.4f}", kind="channel"),
        label=label[:64],
        freq_mhz=lead.channel.freq_mhz,
        tx_freq_mhz=lead.channel.tx_freq_mhz,
        mode=mode,
        tone=tone,
        tx_tone=tx_tone,
        service_type=13,
        avoid=avoid,
        notes=notes,
        lat=position.channel.lat if position is not None else None,
        lon=position.channel.lon if position is not None else None,
        location_precision=(position.channel.location_precision or "unknown") if position is not None else "",
        dv_urcall="CQCQCQ" if lead.family == "DV" else "",
        dv_rpt1=f"{call:<7}{module}" if lead.family == "DV" and call else "",
        dv_rpt2=f"{call:<7}G" if lead.family == "DV" and call else "",
        nxdn_ran=ran,
    )
    return state, group, channel


_GROUP_ORDER = [label for _low, _high, label in _BANDS] + ["Analog Other", "D-STAR", "P25 Digital", "NXDN Digital"]


def build_registry(catalog: Catalog, home: Optional[Tuple[float, float]] = None) -> Optional[FavoritesList]:
    """HAMREG from the catalog's repeater lists, or ``None`` when there are none."""
    if home is None:
        from wasds150.plans.template import HOME

        home = HOME
    grouped: "OrderedDict[Tuple[str, str], List[Channel]]" = OrderedDict()
    ids = set()
    machines = _machines(_copies(catalog))
    dstar_sides = {
        (m[0].call, round(m[0].channel.freq_mhz, 4)) for m in machines if m[0].family == "DV" and m[0].call
    }

    routed: Dict[str, Tuple[bool, Tuple[str, str], Channel]] = {}

    def keep(state: str, group: str, channel: Channel) -> None:
        if channel.lat is not None and haversine_miles(home[0], home[1], channel.lat, channel.lon) > REACH_MILES:
            return
        routing = channel.dv_rpt1.strip()
        if routing:
            # One module, one machine: a D-STAR list that still carries a
            # repeater's old pair is not a second module (DSTARInfo's W7RNK C
            # on 147.950 against WWARA's 147.995). The coordinated pair wins.
            notes = channel.notes or ""
            coordinated = "registry: WWARA" in notes or notes.startswith("input ")
            previous = routed.get(routing)
            if previous is not None:
                if previous[0] or not coordinated:
                    return
                grouped[previous[1]].remove(previous[2])
            routed[routing] = (coordinated, (state, group), channel)
        while channel.id in ids:  # the same call and output in two places
            channel.id = stable_id(channel.id + ":again", kind="channel")
        ids.add(channel.id)
        grouped.setdefault((state, group), []).append(channel)

    for machine in machines:
        record = _record(machine)
        if record is None:
            continue
        state, group, channel = record
        lead = sorted(machine, key=lambda c: c.rank)[0]
        if lead.family == "DV":
            if not channel.dv_rpt1.strip():
                # A county row calling itself D-STAR with no routing call is
                # not programmable; the machine is whatever else lists it.
                continue
            # Its analog copies are copies of a D-STAR machine: no radio keys
            # them in FM, and the scanner cannot decode them.
            for copy in machine:
                if copy.family == "DV" or copy.source in COORDINATORS:
                    continue
                copy.channel.avoid = True
                note = f"D-STAR only: {channel.dv_rpt1.strip()} (repeater registry)"
                if note not in (copy.channel.notes or ""):
                    copy.channel.notes = "; ".join(part for part in (copy.channel.notes, note) if part)
        keep(state, group, channel)
        # WWARA's mixed FM/D-Star machines: the analog record above, and the
        # D-STAR side here when no D-STAR source already lists it.
        mixed = next((c for c in machine if c.source == WWARA and _MIXED_DSTAR.search(c.channel.notes or "")), None)
        call = next((c.call for c in sorted(machine, key=lambda c: c.rank) if c.call and c.source in NAMING), "")
        if mixed is None or not call or (call, round(channel.freq_mhz, 4)) in dstar_sides:
            continue
        module = _band_value(channel.freq_mhz, _MODULES)
        if not module:
            continue
        side = Channel(
            id=stable_id(f"hamreg:DV:{call} {module}:{channel.freq_mhz:.4f}", kind="channel"),
            label=f"{call} {module} - {channel.label.split(' - ', 1)[1]}"[:64] if " - " in channel.label
            else f"{call} {module}",
            freq_mhz=channel.freq_mhz, tx_freq_mhz=channel.tx_freq_mhz, mode="DV", service_type=13,
            avoid=channel.avoid, lat=channel.lat, lon=channel.lon,
            location_precision=channel.location_precision,
            notes=f"{channel.notes}; D-STAR side of a WWARA FM/D-Star machine; module {module} from the band",
            dv_urcall="CQCQCQ", dv_rpt1=f"{call:<7}{module}", dv_rpt2=f"{call:<7}G",
        )
        dstar_sides.add((call, round(channel.freq_mhz, 4)))
        keep(state, "D-STAR", side)
    if not grouped:
        return None
    departments = []
    for (state, group) in sorted(grouped, key=lambda k: (k[0] != HOME_STATE, k[0], _GROUP_ORDER.index(k[1]))):
        channels = sorted(grouped[(state, group)], key=lambda c: (c.freq_mhz or 0.0, c.label))
        located = [(c.lat, c.lon) for c in channels if c.lat is not None]
        lat = lon = radius = None
        if located:
            lat = sum(p[0] for p in located) / len(located)
            lon = sum(p[1] for p in located) / len(located)
            radius = math.ceil(max(haversine_miles(lat, lon, p[0], p[1]) for p in located) + 10.0)
        departments.append(Department(
            id=stable_id(f"hamreg:{state}:{group}", kind="department"),
            label=f"{state} - {group}"[:64],
            channels=channels,
            lat=round(lat, 6) if lat is not None else None,
            lon=round(lon, 6) if lon is not None else None,
            range_miles=radius,
            shape="Circle" if lat is not None else "",
        ))
    total = sum(len(d.channels) for d in departments)
    return FavoritesList(
        id=stable_id(REGISTRY_KEY.lower()),
        slug=REGISTRY_KEY.lower(),
        favorite_key=REGISTRY_KEY,
        favorite_name="Amateur Repeater Registry",
        region="Washington and neighbours",
        counties="Station locations",
        scenario="Every amateur repeater the catalog knows, one record per machine",
        source_type="Merged: WWARA, IACC, operator-published, DSTARInfo, RadioReference, RepeaterBook, FTX-1 import",
        system_or_category=f"{len(departments)} state and band groups",
        sites_or_coverage=f"Within {REACH_MILES:.0f} miles of home",
        departments_or_channels=f"{total} repeaters",
        mode="FM/NFM, D-STAR, P25, NXDN",
        monitorability="Analog native; D-STAR, P25 and NXDN as each radio supports",
        upgrade_required="",
        source_url="",
        notes="Rebuilt from the catalog on every load; each record's note names its sources.",
        enabled=True,
        origin=ORIGIN_LOCAL,
        systems=[System(id=stable_id("hamreg:system", kind="system"), label="Amateur Repeater Registry", departments=departments)],
        provenance=[Provenance(source_adapter="derived_registry", source_url="catalog://HAMREG", confidence="derived")],
    )


def place_registry(catalog: Catalog) -> int:
    """Rebuild HAMREG in ``catalog``. Returns how many repeaters it holds."""
    catalog.favorites = [f for f in catalog.favorites if f.favorite_key.upper() != REGISTRY_KEY]
    registry = build_registry(catalog)
    if registry is None:
        return 0
    catalog.favorites.append(registry)
    return sum(len(d.channels) for s in registry.systems for d in s.departments)
