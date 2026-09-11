"""RadioReference Database Web Service (SOAP): live trunked-system data.

For every trunked system the catalog names by SID (``SID 7971`` in a row's
text), this adapter asks the service for the system's details
(``getTrsDetails``), its sites and their frequencies (``getTrsSites``), its
talkgroups (``getTrsTalkgroups``) and talkgroup categories
(``getTrsTalkgroupCats``), plus the trunking type table once
(``getTrsType``), and builds a complete scanner system from them: sites with
their coverage circles, the site frequency table, and one talkgroup
department per RadioReference category. Only Project 25 systems are built;
the scanner file writer has no other trunking technology.

**Authentication.** Every data call needs a RadioReference Premium username
and password as well as the application key (``getCountryList`` is the only
call that answers with the key alone). The key and username live in the
local ``state/sources.json`` (``wasds150 sources configure --rr-app-key``,
``--rr-username``). The password is read at run time from the
``WASDS150_RR_PASSWORD`` environment variable or from Windows Credential
Manager, where ``cmdkey /generic:wasds150-radioreference /user:<name> /pass``
stores it (the generic credential's user name also supplies the username).
It is never written to disk, logged, or echoed in an error message.

**Licensing.** This is data the operator is licensed to use personally. The
systems it produces land in the local catalog only, are matched to rows by
exact SID (see :mod:`wasds150.recipes.engine`), and replace older copies of
the same system - a Sentinel HPDB import or a previous refresh - because
the web service is the current record.
"""
from __future__ import annotations

import datetime
import os
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from wasds150.models.catalog import Channel, Department, Site, System, TrunkFrequency
from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult
from wasds150.sources.radioreference_premium import RadioReferenceCredentials
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
#: Seconds between requests. The service is shared and a full refresh is
#: about seventy calls, so there is no reason to hurry it.
REQUEST_SPACING = 0.25
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
            "sites": self.call("getTrsSites", sid=sid) or [],
            "talkgroups": self.call("getTrsTalkgroups", sid=sid, tgCid=0, tgTag=0, tgDec=0) or [],
            "categories": self.call("getTrsTalkgroupCats", sid=sid) or [],
        }


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


def _service_type(tags: Any) -> Optional[int]:
    from wasds150.recipes.rr_county import _service_type as by_tag

    for tag in tags if isinstance(tags, list) else []:
        code = by_tag(str((tag or {}).get("tagDescr") or ""))
        if code is not None:
            return code
    return None


def _is_p25(record: Dict[str, Any]) -> Tuple[bool, str]:
    names = {int(t["sType"]): str(t.get("sTypeDescr") or "") for t in record.get("types") or [] if t.get("sType") is not None}
    stype = (record.get("details") or {}).get("sType")
    description = names.get(stype, f"type {stype}")
    return ("project 25" in description.lower() or "p25" in description.lower()), description


def system_from_api(record: Dict[str, Any]) -> Tuple[Optional[System], List[str]]:
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
            service_type=_service_type(tg.get("tags")),
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
        for entry in site.get("siteFreqs") or []:
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
    sysids = details.get("sysid") or []
    wacn = next((str(s.get("wacn")) for s in sysids if isinstance(s, dict) and s.get("wacn")), None)
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
    ):
        self.credentials = credentials or RadioReferenceCredentials()
        self.sids = tuple(sids) if sids is not None else None
        self.api = api

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        # SOAP is POST-only, so the shared GET cache (http_client) is unused.
        if not self.credentials.is_configured():
            raise RadioReferenceApiError(LOGIN_HELP)
        api = self.api or RadioReferenceApi(self.credentials)
        sids = self.sids if self.sids is not None else catalog_system_ids()
        types = api.call("getTrsType") or []
        systems, errors = [], []
        for sid in sids:
            try:
                systems.append(api.trunked_system(sid, types))
            except RadioReferenceApiError as exc:
                errors.append(f"SID {sid}: {exc}")
        if errors and not systems:
            raise RadioReferenceApiError(errors[0])
        return RawDoc(
            source_adapter=self.name,
            payload={"systems": systems, "errors": errors, "calls": api.calls},
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        facts: List[NormalizedFact] = []
        warnings: List[str] = list(raw.payload.get("errors") or [])
        for record in raw.payload.get("systems") or []:
            system, notes = system_from_api(record)
            warnings.extend(notes)
            if system is None:
                continue
            talkgroups = sum(len(d.channels) for site in system.sites for d in site.departments)
            facts.append(NormalizedFact(
                entity_key=f"{SOURCE_ID}:TrunkId:{system.sid}",
                fact_type="system",
                name=system.label,
                source_id=SOURCE_ID,
                source_url=SID_URL.format(system.sid),
                retrieved_at=raw.fetched_at,
                raw={
                    "sid": system.sid,
                    "sid_kind": "TrunkId",
                    "system": system.to_dict(),
                    "talkgroups": talkgroups,
                    "sites": len(system.sites),
                    "frequencies": len(system.trunk_frequencies),
                },
            ))
        return NormalizeResult(facts=facts, warnings=warnings)
