"""Fail-closed semantic validation for generated SDS150 artifacts.

Schema arity is necessary but not sufficient: a file can have the right
number of tab-separated columns while containing an impossible frequency,
an orphan channel, an invalid tone, or no scannable content.  Every
generation/install path calls this module before publishing bytes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from wasds150.hpe import codec, schema
from wasds150.hpe.record import Record, RecordDocument, parse_records, serialize_records
from wasds150.models.catalog import Channel, Department, FavoritesList, Site, System
from wasds150.radios.registry import SDS150

#: The HPE writer only ever targets the SDS150, so its coverage and
#: modulation limits come from that radio's capability profile.  Keeping them
#: in one place means a second radio cannot silently inherit them.
_PROFILE = SDS150
_SCANNER_BANDS: Tuple[Tuple[float, float], ...] = _PROFILE.rx_bands
_MODES = set(_PROFILE.modes)
_TONE_RE = re.compile(
    r"^(?:TONE=C\d{1,3}(?:\.\d{1,2})?|(?:TONE=)?D\d{3}|"
    r"NAC=(?:[0-9A-Fa-f]{1,3}|Srch)|ColorCode=\d{1,2})$"
)
_GENERATED_TAGS = {
    "TargetModel", "FormatVersion", "Conventional", "C-Group", "C-Freq",
    "Trunk", "Site", "T-Group", "TGID", "T-Freq", "DQKs_Status",
    "BandPlan_P25", "BandPlan_Mot", "Rectangle", "File",
}


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class HpeValidationError(ValueError):
    def __init__(self, context: str, issues: Sequence[ValidationIssue]):
        self.context = context
        self.issues = list(issues)
        super().__init__(f"{context} failed validation: " + "; ".join(str(issue) for issue in self.issues))


def frequency_is_scannable(freq_mhz: float) -> bool:
    return _PROFILE.can_receive(freq_mhz)


def tone_is_valid(tone: str) -> bool:
    if not _TONE_RE.fullmatch(tone):
        return False
    if tone.startswith("TONE=C"):
        try:
            return 60.0 <= float(tone.removeprefix("TONE=C")) <= 260.0
        except ValueError:
            return False
    dcs = tone.removeprefix("TONE=")
    if dcs.startswith("D"):
        return all(digit in "01234567" for digit in dcs[1:])
    if tone.startswith("ColorCode="):
        try:
            return 0 <= int(tone.removeprefix("ColorCode=")) <= 15
        except ValueError:
            return False
    return True


def _text_issues(value: str, path: str, *, required: bool = True) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if required and not value.strip():
        issues.append(ValidationIssue("empty-name", f"{path} must not be blank"))
    if any(ch in value for ch in ("\t", "\r", "\n")):
        issues.append(ValidationIssue("unsafe-text", f"{path} contains a tab or newline"))
    try:
        value.encode("ascii")
    except UnicodeEncodeError:
        issues.append(ValidationIssue("non-ascii", f"{path} is not ASCII encodable"))
    return issues


def _geo_issues(lat: Optional[float], lon: Optional[float], range_miles: Optional[float], path: str) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if (lat is None) != (lon is None):
        issues.append(ValidationIssue("partial-geo", f"{path} must provide both latitude and longitude"))
    if lat is not None and not -90 <= lat <= 90:
        issues.append(ValidationIssue("invalid-latitude", f"{path} latitude {lat} is outside -90..90"))
    if lon is not None and not -180 <= lon <= 180:
        issues.append(ValidationIssue("invalid-longitude", f"{path} longitude {lon} is outside -180..180"))
    if range_miles is not None and range_miles < 0:
        issues.append(ValidationIssue("invalid-range", f"{path} range {range_miles} must be non-negative"))
    return issues


def _channel_issues(channel: Channel, path: str, *, trunked: bool) -> List[ValidationIssue]:
    issues = _text_issues(channel.label, f"{path}.label")
    issues.extend(_text_issues(channel.id, f"{path}.id"))
    if trunked:
        if channel.tgid is None:
            issues.append(ValidationIssue("missing-tgid", f"{path} is trunked but has no TGID"))
        elif not 0 <= channel.tgid <= 0xFFFFFFFF:
            issues.append(ValidationIssue("invalid-tgid", f"{path} TGID {channel.tgid} is outside 0..4294967295"))
        if channel.freq_mhz is not None:
            issues.append(ValidationIssue("trunk-channel-frequency", f"{path} must not carry a conventional frequency"))
    else:
        if channel.freq_mhz is None:
            issues.append(ValidationIssue("missing-frequency", f"{path} is conventional but has no frequency"))
        elif not frequency_is_scannable(channel.freq_mhz):
            issues.append(ValidationIssue("unsupported-frequency", f"{path} frequency {channel.freq_mhz:g} MHz is outside SDS150 coverage"))
        if channel.tgid is not None:
            issues.append(ValidationIssue("conventional-tgid", f"{path} must not carry a TGID"))
    if channel.mode and channel.mode.upper() not in _MODES:
        issues.append(ValidationIssue("invalid-mode", f"{path} mode {channel.mode!r} is not supported"))
    if channel.tone and not tone_is_valid(channel.tone):
        issues.append(ValidationIssue("invalid-tone", f"{path} tone {channel.tone!r} is not BCDx36HP syntax"))
    if channel.service_type is not None and channel.service_type not in schema.SERVICE_TYPES:
        issues.append(ValidationIssue("invalid-service-type", f"{path} service type {channel.service_type} is unknown"))
    return issues


def _department_issues(department: Department, path: str, *, trunked: bool) -> List[ValidationIssue]:
    issues = _text_issues(department.label, f"{path}.label")
    issues.extend(_text_issues(department.id, f"{path}.id"))
    issues.extend(_geo_issues(department.lat, department.lon, department.range_miles, path))
    if not department.channels:
        issues.append(ValidationIssue("empty-department", f"{path} contains no channels"))
    seen = set()
    for index, channel in enumerate(department.channels):
        channel_path = f"{path}.channels[{index}]"
        issues.extend(_channel_issues(channel, channel_path, trunked=trunked))
        key = (channel.label.casefold(), channel.freq_mhz, channel.tgid)
        if key in seen:
            issues.append(ValidationIssue("duplicate-channel", f"{channel_path} duplicates label/frequency/TGID in {path}"))
        seen.add(key)
    return issues


def _site_issues(site: Site, path: str) -> List[ValidationIssue]:
    issues = _text_issues(site.label, f"{path}.label")
    issues.extend(_text_issues(site.id, f"{path}.id"))
    issues.extend(_geo_issues(site.lat, site.lon, site.range_miles, path))
    for index, department in enumerate(site.departments):
        issues.extend(_department_issues(department, f"{path}.departments[{index}]", trunked=True))
    return issues


def system_is_trunked(system: System) -> bool:
    return bool(system.sites or system.trunk_frequencies or system.sid or system.wacn or system.tech)


def validate_systems(systems: Iterable[System]) -> List[ValidationIssue]:
    systems = list(systems)
    issues: List[ValidationIssue] = []
    if not systems:
        return [ValidationIssue("empty-favorites-list", "no systems were supplied")]
    ids = set()
    for system_index, system in enumerate(systems):
        path = f"systems[{system_index}]"
        issues.extend(_text_issues(system.label, f"{path}.label"))
        issues.extend(_text_issues(system.id, f"{path}.id"))
        if system.id in ids:
            issues.append(ValidationIssue("duplicate-system-id", f"{path}.id {system.id!r} is duplicated"))
        ids.add(system.id)
        trunked = system_is_trunked(system)
        if trunked:
            if system.departments:
                issues.append(ValidationIssue("mixed-system-shape", f"{path} is trunked but also has conventional departments"))
            if not system.sites:
                issues.append(ValidationIssue("missing-sites", f"{path} is trunked but has no sites"))
            if not system.trunk_frequencies:
                issues.append(ValidationIssue("missing-trunk-frequencies", f"{path} is trunked but has no site frequencies"))
            if not any(site.departments for site in system.sites):
                issues.append(ValidationIssue("missing-talkgroups", f"{path} is trunked but has no talkgroup departments"))
            for site_index, site in enumerate(system.sites):
                issues.extend(_site_issues(site, f"{path}.sites[{site_index}]"))
            for freq_index, trunk_frequency in enumerate(system.trunk_frequencies):
                freq_path = f"{path}.trunk_frequencies[{freq_index}]"
                issues.extend(_text_issues(trunk_frequency.id, f"{freq_path}.id"))
                if trunk_frequency.freq_mhz is None:
                    issues.append(ValidationIssue("missing-trunk-frequency", f"{freq_path} has no frequency"))
                elif not frequency_is_scannable(trunk_frequency.freq_mhz):
                    issues.append(ValidationIssue("unsupported-frequency", f"{freq_path} frequency {trunk_frequency.freq_mhz:g} MHz is outside SDS150 coverage"))
        else:
            if not system.departments:
                issues.append(ValidationIssue("empty-system", f"{path} contains no conventional departments"))
            for department_index, department in enumerate(system.departments):
                issues.extend(_department_issues(department, f"{path}.departments[{department_index}]", trunked=False))
    return issues


def validate_favorites_list(favorites_list: FavoritesList) -> List[ValidationIssue]:
    issues = _text_issues(favorites_list.favorite_key, "favorite_key")
    issues.extend(_text_issues(favorites_list.favorite_name, "favorite_name"))
    issues.extend(validate_systems(favorites_list.systems))
    return issues


def _record_field(record: Record, field_name: str) -> str:
    tag_schema = schema.BCDX36HP_SCHEMA.get(record.tag)
    spec = tag_schema.field_by_name(field_name) if tag_schema else None
    return record.get(spec.index - 1, "") if spec else ""


def validate_document(document: RecordDocument) -> List[ValidationIssue]:
    issues = [ValidationIssue("schema", issue) for issue in schema.validate_schema(document)]
    records = document.records
    if not records:
        return issues + [ValidationIssue("empty-document", "document has no records")]
    if len(document.line_endings) != len(records) or any(ending != "\r\n" for ending in document.line_endings):
        issues.append(ValidationIssue("line-endings", "generated records must all use CRLF line endings"))
    if records[0].tag != "TargetModel" or records[0].fields != ["BCDx36HP"]:
        issues.append(ValidationIssue("target-model", "first record must be TargetModel BCDx36HP"))
    if len(records) < 2 or records[1].tag != "FormatVersion" or records[1].fields != ["1.00"]:
        issues.append(ValidationIssue("format-version", "second record must be FormatVersion 1.00"))
    signatures = [index for index, record in enumerate(records) if record.tag == "File"]
    if signatures != [len(records) - 1] or records[-1].fields != ["HomePatrol Export File"]:
        issues.append(ValidationIssue("signature", "exactly one HomePatrol signature must be the final record"))
    for record in records:
        if record.tag not in _GENERATED_TAGS:
            issues.append(ValidationIssue("unexpected-tag", f"generated document contains unsupported tag {record.tag!r}"))

    current_system = None
    current_group = None
    current_site = None
    content_records = 0
    for index, record in enumerate(records[2:-1], start=2):
        path = f"records[{index}]({record.tag})"
        if record.tag in ("Conventional", "Trunk"):
            current_system, current_group, current_site = record.tag, None, None
            issues.extend(_text_issues(_record_field(record, "name"), f"{path}.name"))
        elif record.tag == "C-Group":
            if current_system != "Conventional":
                issues.append(ValidationIssue("orphan-record", f"{path} is not under a Conventional system"))
            current_group = "C-Group"
            issues.extend(_text_issues(_record_field(record, "name"), f"{path}.name"))
        elif record.tag == "C-Freq":
            if current_system != "Conventional" or current_group != "C-Group":
                issues.append(ValidationIssue("orphan-record", f"{path} is not under a C-Group"))
            content_records += 1
            issues.extend(_text_issues(_record_field(record, "name"), f"{path}.name"))
            raw_freq = _record_field(record, "freq_hz")
            try:
                freq_mhz = int(raw_freq) / 1_000_000
                if not frequency_is_scannable(freq_mhz):
                    raise ValueError
            except (TypeError, ValueError):
                issues.append(ValidationIssue("invalid-frequency", f"{path} has invalid/unsupported frequency {raw_freq!r}"))
            mode = _record_field(record, "mode")
            if mode.upper() not in _MODES:
                issues.append(ValidationIssue("invalid-mode", f"{path} has unsupported mode {mode!r}"))
            tone = _record_field(record, "tone")
            if tone and not tone_is_valid(tone):
                issues.append(ValidationIssue("invalid-tone", f"{path} has invalid tone {tone!r}"))
        elif record.tag == "Site":
            if current_system != "Trunk":
                issues.append(ValidationIssue("orphan-record", f"{path} is not under a Trunk system"))
            current_site, current_group = "Site", None
            issues.extend(_text_issues(_record_field(record, "name"), f"{path}.name"))
        elif record.tag == "T-Group":
            if current_system != "Trunk" or current_site != "Site":
                issues.append(ValidationIssue("orphan-record", f"{path} is not under a Site"))
            current_group = "T-Group"
            issues.extend(_text_issues(_record_field(record, "name"), f"{path}.name"))
        elif record.tag == "TGID":
            if current_system != "Trunk" or current_group != "T-Group":
                issues.append(ValidationIssue("orphan-record", f"{path} is not under a T-Group"))
            content_records += 1
            issues.extend(_text_issues(_record_field(record, "name"), f"{path}.name"))
            try:
                tgid = int(_record_field(record, "tgid"))
                if not 0 <= tgid <= 0xFFFFFFFF:
                    raise ValueError
            except (TypeError, ValueError):
                issues.append(ValidationIssue("invalid-tgid", f"{path} has invalid TGID {_record_field(record, 'tgid')!r}"))
        elif record.tag == "T-Freq":
            if current_system != "Trunk":
                issues.append(ValidationIssue("orphan-record", f"{path} is not under a Trunk system"))
            raw_freq = _record_field(record, "freq_hz")
            try:
                freq_mhz = int(raw_freq) / 1_000_000
                if not frequency_is_scannable(freq_mhz):
                    raise ValueError
            except (TypeError, ValueError):
                issues.append(ValidationIssue("invalid-frequency", f"{path} has invalid/unsupported frequency {raw_freq!r}"))
        elif record.tag in ("DQKs_Status", "BandPlan_P25", "BandPlan_Mot", "Rectangle"):
            # Arity is checked by schema.validate_schema. These records add
            # policy/geometry/band-plan metadata but not scannable content.
            pass
    if content_records == 0:
        issues.append(ValidationIssue("no-scannable-content", "document has no conventional channels or talkgroups"))

    system_starts = [index for index, record in enumerate(records) if record.tag in ("Conventional", "Trunk")]
    for position, start in enumerate(system_starts):
        end = system_starts[position + 1] if position + 1 < len(system_starts) else len(records) - 1
        segment = records[start:end]
        system_record = segment[0]
        tags = [record.tag for record in segment]
        name = _record_field(system_record, "name") or f"record {start}"
        if system_record.tag == "Conventional":
            if "C-Group" not in tags or "C-Freq" not in tags:
                issues.append(ValidationIssue("empty-system", f"Conventional system {name!r} has no group/channel content"))
        else:
            for required_tag, description in (
                ("Site", "site"),
                ("T-Freq", "site frequency"),
                ("T-Group", "talkgroup department"),
                ("TGID", "talkgroup"),
            ):
                if required_tag not in tags:
                    issues.append(ValidationIssue("incomplete-trunk-system", f"Trunk system {name!r} has no {description} records"))
    return issues


def validate_hpe_container(data: bytes) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if len(data) > schema.MAX_FAVORITES_LIST_BYTES:
        issues.append(ValidationIssue("file-size", f"container is {len(data)} bytes; maximum is {schema.MAX_FAVORITES_LIST_BYTES}"))
    try:
        text = codec.decode_container(data)
    except codec.HpeError as exc:
        return issues + [ValidationIssue("container-decode", str(exc))]
    document = parse_records(text)
    issues.extend(validate_document(document))
    if not codec.has_signature_line(text):
        issues.append(ValidationIssue("signature", "decoded text lacks the HomePatrol signature line"))
    if serialize_records(document) != text:
        issues.append(ValidationIssue("record-roundtrip", "parsed records do not serialize byte-for-byte"))
    if codec.encode_container(text) != data:
        issues.append(ValidationIssue("container-determinism", "container is not the canonical deterministic encoding"))
    return issues


def validate_hpe_bytes(favorites_list: FavoritesList, data: bytes) -> List[ValidationIssue]:
    issues = validate_favorites_list(favorites_list)
    issues.extend(validate_hpe_container(data))
    try:
        text = codec.decode_container(data)
    except codec.HpeError:
        return issues

    # Model-to-record parity catches omissions and accidental extra records.
    from wasds150.hpe.builders import build_favorites_document

    expected_text = serialize_records(build_favorites_document(favorites_list.systems))
    if expected_text != text:
        issues.append(ValidationIssue("model-parity", "decoded records do not exactly match the source FavoritesList model"))
    return issues


def require_valid_favorites_list(favorites_list: FavoritesList) -> None:
    issues = validate_favorites_list(favorites_list)
    if issues:
        raise HpeValidationError(f"{favorites_list.favorite_key} ({favorites_list.favorite_name})", issues)


def require_valid_document(document: RecordDocument, *, context: str = "HPE document") -> None:
    issues = validate_document(document)
    if issues:
        raise HpeValidationError(context, issues)


def require_valid_hpe_bytes(favorites_list: FavoritesList, data: bytes) -> None:
    issues = validate_hpe_bytes(favorites_list, data)
    if issues:
        raise HpeValidationError(f"{favorites_list.favorite_key} ({favorites_list.favorite_name})", issues)


def require_valid_hpe_container(data: bytes, *, context: str = "HPE container") -> None:
    issues = validate_hpe_container(data)
    if issues:
        raise HpeValidationError(context, issues)
