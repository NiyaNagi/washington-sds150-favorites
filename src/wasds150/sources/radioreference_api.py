"""RadioReference Database Web Service (SOAP): everything it holds for
Washington, kept fresh, with a report of what changed between runs.

**What a run fetches** (``scope="washington"``, the default):

* lookup tables once: modes (``getMode``), service tags (``getTag``) and
  trunking types (``getTrsType``);
* the state (``getStateInfo``): its 39 counties, its statewide agencies
  (Washington State Patrol, DNR, ...) and every trunked system;
* every county (``getCountyInfo``) and agency (``getAgencyInfo``): their
  categories and subcategories, and the county's trunked systems;
* every subcategory's conventional frequencies (``getSubcatFreqs``);
* every trunked system (``getTrsDetails``, ``getTrsSites``,
  ``getTrsTalkgroups``, ``getTrsTalkgroupCats``). Project 25 systems become
  complete scanner systems; others are recorded and reported, because the
  scanner file writer only builds P25.

``scope="systems"`` (an explicit ``sids=`` list) fetches only those systems.

**Fresh data on every rerun.** The whole pull is persisted as
``<home>/radioreference/snapshot.json``. A rerun asks for the state and every
county and agency again (about seventy calls), then re-fetches a
subcategory only when its county's or agency's ``lastUpdated`` stamp moved,
and a trunked system only when the state's list stamps it newer. At least
every ``full_every_days`` (default 7) it re-fetches everything regardless,
so nothing can drift for long behind a stamp that did not move. The
snapshot is checkpointed while a run goes, so an interrupted run resumes
where it stopped instead of starting again.

**What changed.** Each completed run is compared with the previous complete
snapshot by RadioReference's own stable ids - frequency ``fid``, system
``sid`` + talkgroup decimal, site id - and the result is written as
``<home>/radioreference/runs/<timestamp>.json`` and ``.md``: frequencies
added, removed and changed field by field, talkgroups added/removed/changed,
sites and systems added or removed. The first line of the source's warnings
is the one-line summary, so it shows in the update log.

**Authentication.** Every data call needs a RadioReference Premium username
and password as well as the application key (``getCountryList`` is the only
call that answers with the key alone). The key lives in the local
``state/sources.json``. The login is read at run time from
``WASDS150_RR_USERNAME``/``WASDS150_RR_PASSWORD`` or from Windows Credential
Manager (``cmdkey /generic:wasds150-radioreference /user:<name> /pass``). It is
never written to disk, logged, or echoed in an error message.

**Licensing.** This is data the operator is licensed to use personally. It
is kept in the working home and the local catalog, never in the repository.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from wasds150.models.catalog import Channel, Department, Site, System, TrunkFrequency
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult
from wasds150.sources.radioreference_premium import RadioReferenceCredentials, normalize_mode, parse_rr_tone
from wasds150.util.hashing import stable_id

SOURCE_ID = "radioreference_api"
ENDPOINT = "https://api.radioreference.com/soap2/index.php"
NAMESPACE = "http://api.radioreference.com/soap2"
API_VERSION = "latest"
PASSWORD_ENV = "WASDS150_RR_PASSWORD"
USERNAME_ENV = "WASDS150_RR_USERNAME"
CREDENTIAL_TARGET = "wasds150-radioreference"
#: Every system this adapter builds has an id starting with this, so the
#: engine can tell a live copy from an HPDB one.
SYSTEM_ID_PREFIX = "rrapi:"
SID_URL = "https://www.radioreference.com/db/sid/{}"
SUBCAT_URL = "https://www.radioreference.com/db/subcat/{}"
WASHINGTON_STID = 53
STATEWIDE = "Statewide"
DEFAULT_FULL_EVERY_DAYS = 7
#: Seconds between requests. The service is shared; a full pull is a few
#: thousand calls and there is no reason to hurry it.
REQUEST_SPACING = 0.25
CHECKPOINT_EVERY = 100
SNAPSHOT_VERSION = 1
LOGIN_HELP = (
    "RadioReference login not configured: store it with "
    f"'cmdkey /generic:{CREDENTIAL_TARGET} /user:<RadioReference username> /pass' "
    f"(or set {PASSWORD_ENV} and {USERNAME_ENV}); the app key comes from "
    "'wasds150 sources configure --rr-app-key'"
)

_XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"

#: ``transport(request_body, soap_action) -> response_body``
Transport = Callable[[bytes, str], bytes]


class RadioReferenceApiError(RuntimeError):
    """A SOAP fault or a transport failure. The message never carries the
    request, so it can never carry a credential."""


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


# ---------------------------------------------------------------- credentials
def read_windows_credential(target: str = CREDENTIAL_TARGET) -> Optional[Tuple[str, str]]:
    """``(username, password)`` of a Windows generic credential, or ``None``
    when there is none (or this is not Windows)."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class _FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    class _CREDENTIAL(ctypes.Structure):
        _fields_ = [
            ("Flags", wintypes.DWORD),
            ("Type", wintypes.DWORD),
            ("TargetName", wintypes.LPWSTR),
            ("Comment", wintypes.LPWSTR),
            ("LastWritten", _FILETIME),
            ("CredentialBlobSize", wintypes.DWORD),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", wintypes.DWORD),
            ("AttributeCount", wintypes.DWORD),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", wintypes.LPWSTR),
            ("UserName", wintypes.LPWSTR),
        ]

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(_CREDENTIAL))]
    advapi.CredReadW.restype = wintypes.BOOL
    advapi.CredFree.argtypes = [ctypes.c_void_p]
    pointer = ctypes.POINTER(_CREDENTIAL)()
    if not advapi.CredReadW(target, 1, 0, ctypes.byref(pointer)):  # 1 = CRED_TYPE_GENERIC
        return None
    try:
        credential = pointer.contents
        blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        return credential.UserName or "", blob.decode("utf-16-le") if blob else ""
    finally:
        advapi.CredFree(pointer)


def resolve_credentials(
    app_key: str,
    username: str = "",
    *,
    environ: Optional[Dict[str, str]] = None,
    credential_reader: Optional[Callable[[str], Optional[Tuple[str, str]]]] = read_windows_credential,
) -> RadioReferenceCredentials:
    """The key from configuration; the login from the environment, else from
    Windows Credential Manager. Nothing is ever read from the repository."""
    env = os.environ if environ is None else environ
    user = username or env.get(USERNAME_ENV, "")
    password = env.get(PASSWORD_ENV, "")
    if (not user or not password) and credential_reader is not None:
        stored = credential_reader(CREDENTIAL_TARGET)
        if stored:
            user = user or stored[0]
            password = password or stored[1]
    return RadioReferenceCredentials(username=user, password=password, app_key=app_key or "")


# ------------------------------------------------------------------ SOAP I/O
def _urllib_transport(body: bytes, action: str) -> bytes:
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": action, "User-Agent": "wasds150"},
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        return exc.read()  # a SOAP fault arrives as HTTP 500 with a fault body
    except OSError as exc:
        raise RadioReferenceApiError(f"{action}: RadioReference web service unreachable ({type(exc).__name__})") from None


def _envelope(operation: str, params: Dict[str, Any], credentials: RadioReferenceCredentials) -> bytes:
    args = "".join(f"<{name}>{escape(str(value))}</{name}>" for name, value in params.items())
    auth = (
        "<authInfo>"
        f"<username>{escape(credentials.username)}</username>"
        f"<password>{escape(credentials.password)}</password>"
        f"<appKey>{escape(credentials.app_key)}</appKey>"
        f"<version>{API_VERSION}</version><style>rpc</style>"
        "</authInfo>"
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:rr="{NAMESPACE}"><soapenv:Body><rr:{operation}>{args}{auth}</rr:{operation}>'
        "</soapenv:Body></soapenv:Envelope>"
    ).encode("utf-8")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def decode(element: ET.Element) -> Any:
    """RPC/encoded SOAP -> Python: arrays of ``<item>`` become lists, structs
    become dicts keyed by element name, and scalars follow their ``xsi:type``."""
    children = list(element)
    xsi_type = element.get(_XSI_TYPE, "")
    if children:
        if xsi_type.endswith("Array") or all(_local(child.tag) == "item" for child in children):
            return [decode(child) for child in children]
        return {_local(child.tag): decode(child) for child in children}
    if xsi_type.endswith("Array"):
        return []
    text = (element.text or "").strip()
    kind = xsi_type.split(":")[-1]
    try:
        if kind in ("int", "integer", "long", "short"):
            return int(text) if text else None
        if kind in ("decimal", "float", "double"):
            return float(text) if text else None
    except ValueError:
        return text
    if kind == "boolean":
        return text.lower() in ("1", "true")
    return text


class RadioReferenceApi:
    def __init__(
        self,
        credentials: RadioReferenceCredentials,
        transport: Optional[Transport] = None,
        spacing: float = REQUEST_SPACING,
    ):
        self.credentials = credentials
        self.transport = transport or _urllib_transport
        self.spacing = spacing
        self.calls = 0

    def call(self, operation: str, **params: Any) -> Any:
        body = _envelope(operation, params, self.credentials)
        if self.calls and self.spacing:
            time.sleep(self.spacing)
        self.calls += 1
        payload = self.transport(body, operation)
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            raise RadioReferenceApiError(f"{operation}: the web service returned something that is not XML") from None
        fault = next((e for e in root.iter() if _local(e.tag) == "Fault"), None)
        if fault is not None:
            text = next((e.text for e in fault.iter() if _local(e.tag) == "faultstring"), None) or "SOAP fault"
            raise RadioReferenceApiError(f"{operation}: {text.strip()}")
        response = next((e for e in root.iter() if _local(e.tag) == f"{operation}Response"), None)
        if response is None:
            raise RadioReferenceApiError(f"{operation}: no {operation}Response in the reply")
        value = next(iter(response), None)
        return decode(value) if value is not None else None

    def trunked_system(self, sid: int, types: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Everything this adapter uses about one system, as plain data."""
        return {
            "sid": int(sid),
            "types": list(types),
            "details": self.call("getTrsDetails", sid=sid) or {},
            "sites": _as_list(self.call("getTrsSites", sid=sid)),
            "talkgroups": _as_list(self.call("getTrsTalkgroups", sid=sid, tgCid=0, tgTag=0, tgDec=0)),
            "categories": _as_list(self.call("getTrsTalkgroupCats", sid=sid)),
        }


def _as_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    return [] if value in (None, "", {}) else [value]


def _ids(value: Any, key: str) -> List[int]:
    """Ids out of an id array, whatever shape the service chose for it."""
    ids = []
    for item in _as_list(value):
        raw = item.get(key) if isinstance(item, dict) else item
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    return ids


# ----------------------------------------------------------- system builder
def _clean(text: Any, limit: int = 64) -> str:
    """ASCII, one line, at most ``limit`` characters: what the scanner file takes."""
    return " ".join(str(text or "").encode("ascii", "replace").decode("ascii").split())[:limit]


def _number(value: Any) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _fence(item: Dict[str, Any]) -> Tuple[Optional[float], Optional[float], Optional[float], str]:
    lat, lon, radius = _number(item.get("lat")), _number(item.get("lon")), _number(item.get("range"))
    if lat is None or lon is None or not (lat or lon):
        return None, None, None, ""
    return lat, lon, radius if radius else None, "Circle" if radius else ""


def _tag_names(tags: Any, lookup: Dict[str, str]) -> List[str]:
    names = []
    for tag in _as_list(tags):
        if isinstance(tag, dict):
            name = tag.get("tagDescr") or lookup.get(str(tag.get("tagId")), "")
        else:
            name = lookup.get(str(tag), "")
        if name:
            names.append(str(name))
    return names


def _service_type(tags: Any, lookup: Optional[Dict[str, str]] = None) -> Optional[int]:
    from wasds150.recipes.rr_county import _service_type as by_tag

    for name in _tag_names(tags, lookup or {}):
        code = by_tag(name)
        if code is not None:
            return code
    return None


def _is_p25(record: Dict[str, Any]) -> Tuple[bool, str]:
    names = {int(t["sType"]): str(t.get("sTypeDescr") or "") for t in record.get("types") or [] if t.get("sType") is not None}
    stype = (record.get("details") or {}).get("sType")
    description = names.get(stype, f"type {stype}")
    return ("project 25" in description.lower() or "p25" in description.lower()), description


def system_from_api(record: Dict[str, Any], tag_lookup: Optional[Dict[str, str]] = None) -> Tuple[Optional[System], List[str]]:
    """One trunked :class:`System` from :meth:`RadioReferenceApi.trunked_system`
    data, or ``None`` with the reason."""
    from wasds150.hpe.validation import frequency_is_scannable
    from wasds150.recipes.systems import dedupe_channels

    sid = int(record["sid"])
    details = record.get("details") or {}
    name = _clean(details.get("sName") or f"SID {sid}")
    p25, description = _is_p25(record)
    if not p25:
        return None, [f"SID {sid} {name}: {description} is not Project 25; the scanner file writer only builds P25"]

    categories = {int(c["tgCid"]): c for c in record.get("categories") or [] if c.get("tgCid") is not None}
    grouped: "OrderedDict[int, List[Channel]]" = OrderedDict()
    for tg in sorted(record.get("talkgroups") or [], key=lambda t: (t.get("tgSort") or 0, t.get("tgDec") or 0)):
        dec = tg.get("tgDec")
        if dec is None:
            continue
        enc = int(tg.get("enc") or 0)
        note = "; ".join(part for part in (
            _clean(tg.get("tgDescr"), 120),
            f"RadioReference TG {dec}",
            "encrypted" if enc >= 2 else ("partly encrypted" if enc == 1 else ""),
        ) if part)
        grouped.setdefault(int(tg.get("tgCid") or 0), []).append(Channel(
            id=stable_id(f"{SYSTEM_ID_PREFIX}{sid}:tg:{dec}", kind="channel"),
            label=_clean(tg.get("tgAlpha") or tg.get("tgDescr") or f"TG {dec}"),
            tgid=int(dec),
            mode="ALL",
            service_type=_service_type(tg.get("tags"), tag_lookup),
            avoid=enc >= 2,
            notes=note,
        ))
    departments = []
    for cid, channels in grouped.items():
        category = categories.get(cid, {})
        lat, lon, radius, shape = _fence(category)
        departments.append(Department(
            id=stable_id(f"{SYSTEM_ID_PREFIX}{sid}:cat:{cid}", kind="department"),
            label=_clean(category.get("tgCname") or "Talkgroups"),
            channels=dedupe_channels(channels),
            lat=lat, lon=lon, range_miles=radius, shape=shape,
        ))

    sites: List[Site] = []
    frequencies: List[TrunkFrequency] = []
    seen = set()
    for site in sorted(record.get("sites") or [], key=lambda s: (s.get("siteNumber") or 0, s.get("siteId") or 0)):
        site_id = site.get("siteId")
        number = site.get("siteNumber")
        label = _clean(f"{number:03d} {site.get('siteDescr') or ''}" if isinstance(number, int) else site.get("siteDescr") or f"Site {site_id}")
        lat, lon, radius, shape = _fence(site)
        sites.append(Site(
            id=stable_id(f"{SYSTEM_ID_PREFIX}{sid}:site:{site_id}", kind="site"),
            label=label or f"Site {site_id}", lat=lat, lon=lon, range_miles=radius, shape=shape,
        ))
        for entry in _as_list(site.get("siteFreqs")):
            freq = _number(entry.get("freq"))
            if freq is None or not frequency_is_scannable(freq) or (freq, site_id) in seen:
                continue
            seen.add((freq, site_id))
            lcn = entry.get("lcn")
            frequencies.append(TrunkFrequency(
                id=stable_id(f"{SYSTEM_ID_PREFIX}{sid}:site:{site_id}:{freq}", kind="trunk_frequency"),
                freq_mhz=round(freq, 6),
                lcn=int(lcn) if isinstance(lcn, int) and lcn > 0 else None,
            ))
    if not sites or not frequencies or not departments:
        return None, [f"SID {sid} {name}: RadioReference returned {len(sites)} sites, {len(frequencies)} "
                      f"scannable frequencies and {len(departments)} talkgroup categories; not built"]
    # The HPDB lays talkgroup departments after the last site; mirror it.
    sites[-1].departments = departments
    wacn = next((str(s.get("wacn")) for s in _as_list(details.get("sysid")) if isinstance(s, dict) and s.get("wacn")), None)
    return System(
        id=f"{SYSTEM_ID_PREFIX}TrunkId:{sid}",
        label=name,
        sid=sid,
        wacn=wacn,
        tech="P25Standard",
        sites=sites,
        trunk_frequencies=frequencies,
    ), []


def catalog_system_ids() -> Tuple[int, ...]:
    """Every SID the packaged catalog's rows name: exactly the trunked
    systems the scanner lists are built from."""
    from wasds150.catalog.baseline import load_baseline
    from wasds150.recipes.default_recipes import build_default_recipes

    return tuple(sorted({sid for recipe in build_default_recipes(load_baseline()) for sid in recipe.match.configured_sids()}))


# ------------------------------------------------------------ Washington pull
def _parse_time(text: Any) -> Optional[datetime.datetime]:
    try:
        parsed = datetime.datetime.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=datetime.timezone.utc)


def _lookup(api: RadioReferenceApi, operation: str, id_param: str, id_key: str, name_key: str) -> Dict[str, str]:
    """A lookup table (id 0 asks for all of it); empty if the service refuses."""
    try:
        rows = _as_list(api.call(operation, **{id_param: 0}))
    except RadioReferenceApiError:
        return {}
    return {str(row.get(id_key)): str(row.get(name_key) or "") for row in rows if isinstance(row, dict)}


class WashingtonPull:
    """One run: refreshes what moved since ``previous`` (or everything)."""

    def __init__(
        self,
        api: RadioReferenceApi,
        previous: Optional[Dict[str, Any]] = None,
        *,
        partial: Optional[Dict[str, Any]] = None,
        now: Optional[datetime.datetime] = None,
        full_every_days: int = DEFAULT_FULL_EVERY_DAYS,
        force_full: bool = False,
        extra_sids: Iterable[int] = (),
        checkpoint: Optional[Callable[[Dict[str, Any]], None]] = None,
        checkpoint_every: int = CHECKPOINT_EVERY,
    ):
        self.api = api
        self.previous = previous or {}
        self.now = now or _now()
        last_full = _parse_time(self.previous.get("last_full_at"))
        self.full = bool(
            force_full or not previous or last_full is None
            or (self.now - last_full) >= datetime.timedelta(days=max(0, full_every_days))
        )
        # An interrupted run's items fetched after it started count as fresh.
        self.partial = partial or {}
        self.partial_started = _parse_time(self.partial.get("started_at"))
        self.extra_sids = tuple(int(s) for s in extra_sids)
        self.checkpoint = checkpoint
        self.checkpoint_every = max(1, checkpoint_every)
        self._last_checkpoint = 0

    def _fresh_from_partial(self, section: str, key: str) -> Optional[Dict[str, Any]]:
        item = (self.partial.get(section) or {}).get(key)
        fetched = _parse_time((item or {}).get("fetched_at"))
        if item and self.partial_started and fetched and fetched >= self.partial_started:
            return item
        return None

    def _maybe_checkpoint(self, snapshot: Dict[str, Any]) -> None:
        if self.checkpoint and self.api.calls - self._last_checkpoint >= self.checkpoint_every:
            self._last_checkpoint = self.api.calls
            self.checkpoint(snapshot)

    def run(self) -> Dict[str, Any]:
        stamp = self.now.isoformat()
        started = self.partial.get("started_at") if self.partial_started else stamp
        snapshot: Dict[str, Any] = {
            "version": SNAPSHOT_VERSION,
            "started_at": started,
            "finished_at": None,
            "complete": False,
            "full": self.full,
            "last_full_at": stamp if self.full else self.previous.get("last_full_at"),
            "lookups": {},
            "state": {},
            "counties": {},
            "agencies": {},
            "subcats": {},
            "systems": {},
            "errors": [],
        }
        api = self.api
        types = _as_list(api.call("getTrsType"))
        snapshot["lookups"] = {
            "modes": _lookup(api, "getMode", "mode", "mode", "modeName"),
            "tags": _lookup(api, "getTag", "id", "tagId", "tagDescr"),
            "types": types,
        }
        state = api.call("getStateInfo", stid=WASHINGTON_STID) or {}
        snapshot["state"] = {k: v for k, v in state.items() if k not in ("trsList",)}
        listed_systems: Dict[int, Any] = {}
        for trs in _as_list(state.get("trsList")):
            if isinstance(trs, dict) and trs.get("sid") is not None:
                listed_systems[int(trs["sid"])] = trs.get("lastUpdated")

        owners: List[Tuple[str, Dict[str, Any]]] = []
        for county in _as_list(state.get("countyList")):
            ctid = county.get("ctid") if isinstance(county, dict) else None
            if ctid is None:
                continue
            info = self._fetch_owner("counties", str(ctid), "getCountyInfo", ctid=int(ctid))
            if info is None:
                continue
            snapshot["counties"][str(ctid)] = info
            owners.append((f"county:{ctid}", info))
            for trs in _as_list(info["info"].get("trsList")):
                if isinstance(trs, dict) and trs.get("sid") is not None:
                    listed_systems.setdefault(int(trs["sid"]), trs.get("lastUpdated"))
            self._maybe_checkpoint(snapshot)
        for agency in _as_list(state.get("agencyList")):
            aid = agency.get("aid") if isinstance(agency, dict) else None
            if aid is None:
                continue
            info = self._fetch_owner("agencies", str(aid), "getAgencyInfo", aid=int(aid))
            if info is None:
                continue
            snapshot["agencies"][str(aid)] = info
            owners.append((f"agency:{aid}", info))
            self._maybe_checkpoint(snapshot)

        for owner, info in owners:
            body = info["info"]
            owner_name = body.get("countyName") or body.get("agencyName") or owner
            for category in _as_list(body.get("cats")):
                for subcat in _as_list((category or {}).get("subcats")):
                    scid = subcat.get("scid") if isinstance(subcat, dict) else None
                    if scid is None:
                        continue
                    snapshot["subcats"][str(scid)] = self._subcat(
                        str(scid), owner, str(owner_name), str(category.get("cName") or ""),
                        str(subcat.get("scName") or ""), body.get("lastUpdated"), snapshot,
                    )
                    self._maybe_checkpoint(snapshot)

        for sid in sorted(set(listed_systems) | set(self.extra_sids)):
            entry = self._system(sid, listed_systems.get(sid), types, snapshot)
            if entry is not None:
                snapshot["systems"][str(sid)] = entry
            self._maybe_checkpoint(snapshot)

        snapshot["complete"] = True
        snapshot["finished_at"] = _now().isoformat() if self.now is None else self.now.isoformat()
        return snapshot

    def _fetch_owner(self, section: str, key: str, operation: str, **params: Any) -> Optional[Dict[str, Any]]:
        partial = self._fresh_from_partial(section, key)
        if partial is not None:
            return partial
        try:
            return {"info": self.api.call(operation, **params) or {}, "fetched_at": _now().isoformat()}
        except RadioReferenceApiError as exc:
            previous = (self.previous.get(section) or {}).get(key)
            if previous is not None:
                return previous
            raise RadioReferenceApiError(f"{operation} {params}: {exc}") from None

    def _subcat(self, scid: str, owner: str, owner_name: str, category: str, subcategory: str,
                owner_updated: Any, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        partial = self._fresh_from_partial("subcats", scid)
        if partial is not None:
            return partial
        previous = (self.previous.get("subcats") or {}).get(scid)
        if (not self.full and previous and previous.get("owner_updated") == owner_updated
                and owner_updated not in (None, "")):
            return dict(previous, owner=owner, owner_name=owner_name, category=category, subcategory=subcategory)
        try:
            freqs = _as_list(self.api.call("getSubcatFreqs", scid=int(scid)))
        except RadioReferenceApiError as exc:
            snapshot["errors"].append(f"subcategory {scid} ({owner_name} {category} {subcategory}): {exc}")
            if previous:
                return previous
            freqs = []
        return {
            "owner": owner, "owner_name": owner_name, "category": category, "subcategory": subcategory,
            "owner_updated": owner_updated, "freqs": freqs, "fetched_at": _now().isoformat(),
        }

    def _system(self, sid: int, listed_updated: Any, types: list, snapshot: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = str(sid)
        partial = self._fresh_from_partial("systems", key)
        if partial is not None:
            return partial
        previous = (self.previous.get("systems") or {}).get(key)
        if (not self.full and previous and listed_updated not in (None, "")
                and previous.get("last_updated") == listed_updated):
            return previous
        try:
            record = self.api.trunked_system(sid, types)
        except RadioReferenceApiError as exc:
            snapshot["errors"].append(f"SID {sid}: {exc}")
            return previous
        return {"record": record, "last_updated": listed_updated, "fetched_at": _now().isoformat()}


# ---------------------------------------------------------------- change diff
_FREQ_FIELDS = ("out", "in", "tone", "mode", "descr", "alpha", "callsign", "enc", "colorCode", "tg", "slot")
_TG_FIELDS = ("tgAlpha", "tgDescr", "tgMode", "enc", "tgCid")


def _freq_index(snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    index = {}
    for scid, subcat in (snapshot.get("subcats") or {}).items():
        where = " / ".join(p for p in (subcat.get("owner_name"), subcat.get("category"), subcat.get("subcategory")) if p)
        for freq in _as_list(subcat.get("freqs")):
            if isinstance(freq, dict) and freq.get("fid") is not None:
                index[str(freq["fid"])] = {"where": where, "scid": scid, "freq": freq}
    return index


def _tg_index(snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    index = {}
    for sid, entry in (snapshot.get("systems") or {}).items():
        record = (entry or {}).get("record") or {}
        name = (record.get("details") or {}).get("sName") or f"SID {sid}"
        for tg in _as_list(record.get("talkgroups")):
            if isinstance(tg, dict) and tg.get("tgDec") is not None:
                index[f"{sid}:{tg['tgDec']}"] = {"system": name, "sid": sid, "tg": tg}
    return index


def _site_index(snapshot: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    index = {}
    for sid, entry in (snapshot.get("systems") or {}).items():
        record = (entry or {}).get("record") or {}
        name = (record.get("details") or {}).get("sName") or f"SID {sid}"
        for site in _as_list(record.get("sites")):
            if isinstance(site, dict) and site.get("siteId") is not None:
                freqs = sorted(f.get("freq") for f in _as_list(site.get("siteFreqs")) if isinstance(f, dict) and f.get("freq") is not None)
                index[f"{sid}:{site['siteId']}"] = {"system": name, "site": site.get("siteDescr") or "", "freqs": freqs}
    return index


def _field_changes(old: Dict[str, Any], new: Dict[str, Any], fields: Sequence[str]) -> Dict[str, List[Any]]:
    return {field: [old.get(field), new.get(field)] for field in fields if old.get(field) != new.get(field)}


def diff_snapshots(old: Optional[Dict[str, Any]], new: Dict[str, Any]) -> Dict[str, Any]:
    """What changed from ``old`` to ``new``, keyed by RadioReference's ids."""
    if not old:
        freqs, tgs = _freq_index(new), _tg_index(new)
        return {
            "baseline": True, "from": None, "to": new.get("finished_at"),
            "summary": {
                "frequencies": len(freqs), "talkgroups": len(tgs),
                "systems": len(new.get("systems") or {}), "subcategories": len(new.get("subcats") or {}),
            },
        }
    report: Dict[str, Any] = {"baseline": False, "from": old.get("finished_at"), "to": new.get("finished_at")}
    for name, index_fn, fields in (("frequencies", _freq_index, _FREQ_FIELDS), ("talkgroups", _tg_index, _TG_FIELDS)):
        before, after = index_fn(old), index_fn(new)
        payload_key = "freq" if name == "frequencies" else "tg"
        changed = []
        for key in sorted(set(before) & set(after)):
            delta = _field_changes(before[key][payload_key], after[key][payload_key], fields)
            if delta:
                changed.append(dict(after[key], key=key, changes=delta))
        report[name] = {
            "added": [dict(after[k], key=k) for k in sorted(set(after) - set(before))],
            "removed": [dict(before[k], key=k) for k in sorted(set(before) - set(after))],
            "changed": changed,
        }
    before, after = _site_index(old), _site_index(new)
    report["sites"] = {
        "added": [dict(after[k], key=k) for k in sorted(set(after) - set(before))],
        "removed": [dict(before[k], key=k) for k in sorted(set(before) - set(after))],
        "frequencies_changed": [
            dict(after[k], key=k, added=sorted(set(after[k]["freqs"]) - set(before[k]["freqs"])),
                 removed=sorted(set(before[k]["freqs"]) - set(after[k]["freqs"])))
            for k in sorted(set(before) & set(after)) if before[k]["freqs"] != after[k]["freqs"]
        ],
    }
    old_systems, new_systems = set(old.get("systems") or {}), set(new.get("systems") or {})
    report["systems"] = {"added": sorted(new_systems - old_systems), "removed": sorted(old_systems - new_systems)}
    report["summary"] = {
        f"{section}_{kind}": len(report[section][kind])
        for section in ("frequencies", "talkgroups") for kind in ("added", "removed", "changed")
    }
    report["summary"].update({
        "sites_added": len(report["sites"]["added"]), "sites_removed": len(report["sites"]["removed"]),
        "site_frequency_changes": len(report["sites"]["frequencies_changed"]),
        "systems_added": len(report["systems"]["added"]), "systems_removed": len(report["systems"]["removed"]),
    })
    return report


def summary_line(report: Dict[str, Any]) -> str:
    s = report.get("summary") or {}
    if report.get("baseline"):
        return (f"RadioReference Washington baseline: {s.get('frequencies', 0):,} frequencies in "
                f"{s.get('subcategories', 0):,} subcategories, {s.get('systems', 0)} trunked systems, "
                f"{s.get('talkgroups', 0):,} talkgroups")
    return (
        f"RadioReference changes since {report.get('from')}: frequencies +{s.get('frequencies_added', 0)} "
        f"-{s.get('frequencies_removed', 0)} ~{s.get('frequencies_changed', 0)}; talkgroups "
        f"+{s.get('talkgroups_added', 0)} -{s.get('talkgroups_removed', 0)} ~{s.get('talkgroups_changed', 0)}; "
        f"sites +{s.get('sites_added', 0)} -{s.get('sites_removed', 0)}; systems "
        f"+{s.get('systems_added', 0)} -{s.get('systems_removed', 0)}"
    )


def report_markdown(report: Dict[str, Any], limit: int = 300) -> str:
    lines = ["# RadioReference Washington changes", "", summary_line(report), ""]
    if report.get("baseline"):
        lines.append("First complete pull: nothing to compare against yet. The next run reports changes.")
        return "\n".join(lines) + "\n"

    def freq_line(item: Dict[str, Any]) -> str:
        f = item.get("freq") or {}
        return f"- {f.get('out')} MHz {f.get('alpha') or ''} - {f.get('descr') or ''} ({item.get('where')}, fid {item.get('key')})"

    def tg_line(item: Dict[str, Any]) -> str:
        t = item.get("tg") or {}
        return f"- {item.get('system')}: TG {t.get('tgDec')} {t.get('tgAlpha') or ''} - {t.get('tgDescr') or ''}"

    for title, section, fmt in (("Frequencies", "frequencies", freq_line), ("Talkgroups", "talkgroups", tg_line)):
        for kind in ("added", "removed", "changed"):
            items = report[section][kind]
            if not items:
                continue
            lines += [f"## {title} {kind} ({len(items)})", ""]
            for item in items[:limit]:
                line = fmt(item)
                if kind == "changed":
                    line += ": " + "; ".join(f"{k} {v[0]!r} -> {v[1]!r}" for k, v in item["changes"].items())
                lines.append(line)
            if len(items) > limit:
                lines.append(f"- ... and {len(items) - limit} more (see the .json report)")
            lines.append("")
    sites = report["sites"]
    for kind in ("added", "removed"):
        if sites[kind]:
            lines += [f"## Sites {kind} ({len(sites[kind])})", ""]
            lines += [f"- {s['system']}: {s['site']}" for s in sites[kind][:limit]] + [""]
    if sites["frequencies_changed"]:
        lines += [f"## Site frequency changes ({len(sites['frequencies_changed'])})", ""]
        lines += [f"- {s['system']}: {s['site']}: +{s['added']} -{s['removed']}" for s in sites["frequencies_changed"][:limit]] + [""]
    for kind in ("added", "removed"):
        if report["systems"][kind]:
            lines += [f"## Systems {kind}", "", "- SID " + ", ".join(report["systems"][kind]), ""]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------- snapshot store
class SnapshotStore:
    """``<home>/radioreference``: the last complete pull, the checkpoint of a
    run in progress, and one change report per completed run."""

    def __init__(self, directory: Path):
        self.directory = Path(directory)

    @property
    def snapshot_path(self) -> Path:
        return self.directory / "snapshot.json"

    @property
    def partial_path(self) -> Path:
        return self.directory / "snapshot.partial.json"

    def _read(self, path: Path) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            return None

    def _write(self, path: Path, data: Dict[str, Any]) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        os.replace(tmp, path)

    def load(self) -> Optional[Dict[str, Any]]:
        return self._read(self.snapshot_path)

    def load_partial(self) -> Optional[Dict[str, Any]]:
        return self._read(self.partial_path)

    def checkpoint(self, snapshot: Dict[str, Any]) -> None:
        self._write(self.partial_path, snapshot)

    def commit(self, snapshot: Dict[str, Any], report: Dict[str, Any]) -> Tuple[Path, Path]:
        self._write(self.snapshot_path, snapshot)
        try:
            self.partial_path.unlink()
        except FileNotFoundError:
            pass
        runs = self.directory / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        stamp = str(snapshot.get("finished_at") or _now().isoformat()).replace(":", "").replace("+0000", "Z")[:17]
        json_path = runs / f"{stamp}.json"
        md_path = runs / f"{stamp}.md"
        json_path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str), encoding="utf-8")
        md_path.write_text(report_markdown(report), encoding="utf-8")
        return json_path, md_path


# ----------------------------------------------------------------- the facts
def _county_names(snapshot: Dict[str, Any]) -> Dict[int, str]:
    names = {}
    for ctid, entry in (snapshot.get("counties") or {}).items():
        name = ((entry or {}).get("info") or {}).get("countyName")
        if name:
            names[int(ctid)] = str(name)
    for county in _as_list((snapshot.get("state") or {}).get("countyList")):
        if isinstance(county, dict) and county.get("ctid") is not None and county.get("countyName"):
            names.setdefault(int(county["ctid"]), str(county["countyName"]))
    return names


def _mode_name(value: Any, modes: Dict[str, str]) -> str:
    text = str(value or "").strip()
    return modes.get(text, text)


def frequency_facts(snapshot: Dict[str, Any], retrieved_at: str) -> List[NormalizedFact]:
    """Every conventional frequency, in the shape the RadioReference county
    lists are built from (see :mod:`wasds150.recipes.rr_county`)."""
    lookups = snapshot.get("lookups") or {}
    modes, tags = lookups.get("modes") or {}, lookups.get("tags") or {}
    facts = []
    for scid, subcat in (snapshot.get("subcats") or {}).items():
        owner = str(subcat.get("owner") or "")
        county = subcat.get("owner_name") if owner.startswith("county:") else STATEWIDE
        category = " ".join(p for p in (subcat.get("category"), subcat.get("subcategory")) if p)
        for freq in _as_list(subcat.get("freqs")):
            out = _number(freq.get("out")) if isinstance(freq, dict) else None
            if not out:
                continue
            tone = parse_rr_tone(freq.get("tone"))
            mode_label = _mode_name(freq.get("mode"), modes)
            input_mhz = _number(freq.get("in"))
            tag_names = _tag_names(freq.get("tags"), tags)
            try:
                color = int(freq.get("colorCode")) if str(freq.get("colorCode") or "").strip() else tone.color_code
            except (TypeError, ValueError):
                color = tone.color_code
            facts.append(NormalizedFact(
                entity_key=f"{SOURCE_ID}:fid:{freq.get('fid')}",
                fact_type="frequency",
                name=_clean(freq.get("descr") or freq.get("alpha") or f"{out:.4f}", 120),
                freq_mhz=out,
                tx_freq_mhz=input_mhz if input_mhz else None,
                tone=tone.tone or None,
                mode=normalize_mode(mode_label),
                county=str(county or STATEWIDE),
                source_id=SOURCE_ID,
                source_url=SUBCAT_URL.format(scid),
                retrieved_at=retrieved_at,
                dmr_color_code=color,
                dmr_timeslot=tone.slot,
                dmr_talkgroup=tone.talkgroup,
                nxdn_ran=tone.ran,
                raw={
                    "fid": freq.get("fid"),
                    "scid": scid,
                    "rr_category": category,
                    "rr_alpha": freq.get("alpha") or "",
                    "rr_callsign": freq.get("callsign") or "",
                    "rr_mode": mode_label,
                    "rr_tone_out": tone.raw,
                    "rr_tag": tag_names[0] if tag_names else "",
                    "tx_tone": tone.tone if tone.tone.startswith(("TONE=", "D")) else "",
                    "enc": freq.get("enc"),
                },
            ))
    return facts


def system_facts(snapshot: Dict[str, Any], retrieved_at: str) -> Tuple[List[NormalizedFact], List[str]]:
    tags = (snapshot.get("lookups") or {}).get("tags") or {}
    counties = _county_names(snapshot)
    facts, notes = [], []
    for sid, entry in sorted((snapshot.get("systems") or {}).items(), key=lambda kv: int(kv[0])):
        record = (entry or {}).get("record")
        if not record:
            continue
        system, reasons = system_from_api(record, tags)
        notes.extend(reasons)
        if system is None:
            continue
        system_counties = [counties[c] for c in _ids((record.get("details") or {}).get("sCounty"), "ctid") if c in counties]
        facts.append(_system_fact(system, retrieved_at, system_counties))
    return facts, notes


def _system_fact(system: System, retrieved_at: str, counties: Sequence[str] = ()) -> NormalizedFact:
    talkgroups = sum(len(d.channels) for site in system.sites for d in site.departments)
    primary = counties[0] if len(counties) == 1 else STATEWIDE
    return NormalizedFact(
        entity_key=f"{SOURCE_ID}:TrunkId:{system.sid}",
        fact_type="system",
        name=system.label,
        county=primary,
        source_id=SOURCE_ID,
        source_url=SID_URL.format(system.sid),
        retrieved_at=retrieved_at,
        raw={
            "sid": system.sid,
            "sid_kind": "TrunkId",
            "system": system.to_dict(),
            "talkgroups": talkgroups,
            "sites": len(system.sites),
            "frequencies": len(system.trunk_frequencies),
            "counties": list(counties),
        },
    )


# ------------------------------------------------------------------ adapter
class RadioReferenceApiSource(OnlineSourceAdapter):
    name = SOURCE_ID
    available = True
    kind = "facts"

    def __init__(
        self,
        credentials: Optional[RadioReferenceCredentials] = None,
        *,
        sids: Optional[Sequence[int]] = None,
        api: Optional[RadioReferenceApi] = None,
        store_dir: Optional[Path] = None,
        full_every_days: int = DEFAULT_FULL_EVERY_DAYS,
        force_full: bool = False,
        now: Optional[datetime.datetime] = None,
        checkpoint_every: int = CHECKPOINT_EVERY,
        extra_sids: Optional[Sequence[int]] = None,
    ):
        #: Systems fetched even if the state's list omits them; ``None`` means
        #: every SID the catalog names.
        self.extra_sids = tuple(extra_sids) if extra_sids is not None else None
        self.credentials = credentials or RadioReferenceCredentials()
        #: An explicit list fetches just those systems; ``None`` pulls the state.
        self.sids = tuple(sids) if sids is not None else None
        self.api = api
        self.store_dir = Path(store_dir) if store_dir is not None else None
        self.full_every_days = full_every_days
        self.force_full = force_full
        self.now = now
        self.checkpoint_every = checkpoint_every

    def _store(self, http_client: Optional[Any]) -> Optional[SnapshotStore]:
        if self.store_dir is not None:
            return SnapshotStore(self.store_dir)
        cache_dir = getattr(getattr(http_client, "store", None), "cache_dir", None)
        if cache_dir is not None:
            # <home>/state/http-cache -> <home>/radioreference
            return SnapshotStore(Path(cache_dir).parent.parent / "radioreference")
        return None

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        # SOAP is POST-only, so the shared GET cache is used only to locate
        # the working home for the snapshot.
        if not self.credentials.is_configured():
            raise RadioReferenceApiError(LOGIN_HELP)
        api = self.api or RadioReferenceApi(self.credentials)
        fetched_at = (self.now or _now()).isoformat()
        if self.sids is not None:
            types = _as_list(api.call("getTrsType"))
            systems, errors = [], []
            for sid in self.sids:
                try:
                    systems.append(api.trunked_system(sid, types))
                except RadioReferenceApiError as exc:
                    errors.append(f"SID {sid}: {exc}")
            if errors and not systems:
                raise RadioReferenceApiError(errors[0])
            return RawDoc(source_adapter=self.name, fetched_at=fetched_at,
                          payload={"scope": "systems", "systems": systems, "errors": errors, "calls": api.calls})

        store = self._store(http_client)
        previous = store.load() if store else None
        partial = store.load_partial() if store else None
        pull = WashingtonPull(
            api, previous, partial=partial, now=self.now, full_every_days=self.full_every_days,
            force_full=self.force_full,
            extra_sids=self.extra_sids if self.extra_sids is not None else catalog_system_ids(),
            checkpoint=store.checkpoint if store else None, checkpoint_every=self.checkpoint_every,
        )
        snapshot = pull.run()
        report = diff_snapshots(previous, snapshot)
        paths = store.commit(snapshot, report) if store else None
        return RawDoc(source_adapter=self.name, fetched_at=fetched_at, payload={
            "scope": "washington", "snapshot": snapshot, "summary": summary_line(report),
            "report_path": str(paths[1]) if paths else "", "calls": api.calls, "full": pull.full,
        })

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        payload = raw.payload or {}
        if payload.get("scope") == "washington":
            snapshot = payload["snapshot"]
            facts = frequency_facts(snapshot, raw.fetched_at)
            systems, notes = system_facts(snapshot, raw.fetched_at)
            where = f"; report {payload['report_path']}" if payload.get("report_path") else ""
            mode = "full" if payload.get("full") else "incremental"
            warnings = [f"{payload.get('summary')} ({mode} run, {payload.get('calls', 0)} calls{where})"]
            warnings += list(snapshot.get("errors") or []) + notes
            return NormalizeResult(facts=facts + systems, warnings=warnings)
        facts: List[NormalizedFact] = []
        warnings: List[str] = list(payload.get("errors") or [])
        for record in payload.get("systems") or []:
            system, reasons = system_from_api(record)
            warnings.extend(reasons)
            if system is not None:
                facts.append(_system_fact(system, raw.fetched_at))
        return NormalizeResult(facts=facts, warnings=warnings)
