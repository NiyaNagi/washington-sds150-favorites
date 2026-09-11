"""Refresh -> review -> apply, plus status, configuration and deletion.

The CLI (:mod:`wasds150.cli_repeaterbook`) and the web UI
(:mod:`wasds150.webui.repeaterbook_api`) both call :class:`RepeaterBookService`,
so the guards live in exactly one place. A refresh passes these, in order,
before anything is sent:

1. the request is inside the policy (allowlisted, verified regions, at most
   three; one centre; a whole-number radius from 1 to 60 miles; at least one
   band the target radio supports);
2. the local enable flag is on (it defaults off, pending RepeaterBook's
   approval) and a valid ``rbuapp_`` token is configured;
3. no other refresh is in flight (requests are never parallel);
4. the token has no authentication block and no 429 lockout;
5. no requested region was requested in the last 60 minutes;
6. the rolling 24-hour budget covers *every* requested region -- otherwise
   nothing is sent at all.

Regions are then requested one at a time. Any failure stops the action: the
remaining regions are not requested and nothing is retried. More than
:data:`~wasds150.sources.repeaterbook.policy.CANDIDATE_CAP` combined candidates
after filtering imports nothing. Retention purges run before and after.
"""
from __future__ import annotations

import datetime
import html
import math
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from wasds150.config import AppConfig
from wasds150.sources.config import SourcesConfig
from wasds150.sources.repeaterbook import policy
from wasds150.sources.repeaterbook.catalog import detail_url, favorite_from_records
from wasds150.sources.repeaterbook.client import (
    AuthError,
    RateLimited,
    RepeaterBookClient,
    RepeaterBookError,
    Transport,
)
from wasds150.sources.repeaterbook.normalize import FilterSpec, filter_records, parse_export
from wasds150.sources.repeaterbook.store import RepeaterBookStore, iso, parse_iso
from wasds150.sources.repeaterbook.token import Token, TokenError, check_token_file_path, load_token

Clock = Callable[[], datetime.datetime]


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class PolicyError(ValueError):
    """The action is outside the approved bounds; nothing was sent."""


class NotEnabledError(PolicyError):
    """The local enable flag is off (pending RepeaterBook approval)."""


class TokenMissingError(PolicyError):
    """No token is configured or set."""


class LimitError(PolicyError):
    """A lockout, cooldown or the 24-hour budget stops the action."""


class CandidateCapError(PolicyError):
    """Too many candidates matched; nothing was imported."""


def attribution() -> Dict[str, str]:
    return {"text": policy.ATTRIBUTION_TEXT, "url": policy.ATTRIBUTION_URL}


ATTRIBUTION_LINE = f"{policy.ATTRIBUTION_TEXT} <{policy.ATTRIBUTION_URL}>"
ATTRIBUTION_MARKDOWN = f"[{policy.ATTRIBUTION_TEXT}]({policy.ATTRIBUTION_URL})"


@dataclass(frozen=True)
class RefreshRequest:
    regions: Tuple[str, ...]
    center: Tuple[float, float]
    radius_mi: int
    bands: Tuple[str, ...]
    radio_id: str


def parse_center(text: str) -> Tuple[float, float]:
    try:
        lat_text, lon_text = (part.strip() for part in str(text).split(","))
        return float(lat_text), float(lon_text)
    except (ValueError, TypeError):
        raise PolicyError("the centre must be 'latitude,longitude', e.g. 47.633,-121.966") from None


def validate_request(request: RefreshRequest) -> Tuple[List[policy.Region], FilterSpec]:
    """Every bound on a refresh, checked before anything else happens."""
    from wasds150.radios.registry import get_profile

    codes = [str(code).strip().upper() for code in request.regions if str(code).strip()]
    if not codes:
        raise PolicyError("choose at least one region")
    if len(set(codes)) != len(codes):
        raise PolicyError("a region may appear only once per action")
    if len(codes) > policy.MAX_REGIONS_PER_ACTION:
        raise PolicyError(f"one action may request at most {policy.MAX_REGIONS_PER_ACTION} regions")
    regions = []
    for code in codes:
        region = policy.REGIONS.get(code)
        if region is None:
            raise PolicyError(f"region {code} is not on the allowlist ({', '.join(sorted(policy.REGIONS))})")
        if not region.verified:
            raise PolicyError(f"region {code} is not enabled: {region.note}")
        regions.append(region)

    try:
        lat, lon = float(request.center[0]), float(request.center[1])
    except (TypeError, ValueError, IndexError):
        raise PolicyError("exactly one centre is required") from None
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise PolicyError("the centre is not a valid latitude,longitude")

    radius = request.radius_mi
    if isinstance(radius, bool) or not isinstance(radius, int):
        raise PolicyError("the radius must be a whole number of miles")
    if not policy.RADIUS_MIN_MI <= radius <= policy.RADIUS_MAX_MI:
        raise PolicyError(f"the radius must be from {policy.RADIUS_MIN_MI} to {policy.RADIUS_MAX_MI} miles")

    try:
        profile = get_profile(request.radio_id)
    except KeyError:
        raise PolicyError(f"unknown radio {request.radio_id!r}") from None
    bands = tuple(dict.fromkeys(str(b).strip().lower() for b in request.bands if str(b).strip()))
    if not bands:
        raise PolicyError("choose at least one band")
    for band in bands:
        if band not in policy.AMATEUR_BANDS:
            raise PolicyError(f"unknown band {band!r} ({', '.join(policy.AMATEUR_BANDS)})")
        low, high = policy.AMATEUR_BANDS[band]
        if not any(lo <= high and low <= hi for lo, hi in profile.rx_bands):
            raise PolicyError(f"the {profile.label} does not support the {band} band")
    return regions, FilterSpec(center=(lat, lon), radius_mi=radius, bands=bands, profile=profile)


def _repo_root() -> Optional[Path]:
    here = Path(__file__).resolve()
    for candidate in here.parents:
        if (candidate / "pyproject.toml").is_file() and (candidate / ".git").exists():
            return candidate
    return None


def purge_on_startup(config: AppConfig, clock: Clock = utc_now) -> None:
    """Apply retention at start-up. Creates nothing if RepeaterBook was never used."""
    store = RepeaterBookStore.for_config(config)
    if store.exists():
        store.purge(clock())


class RepeaterBookService:
    def __init__(
        self,
        config: AppConfig,
        *,
        clock: Clock = utc_now,
        transport: Optional[Transport] = None,
        environ: Optional[Mapping[str, str]] = None,
    ):
        self.config = config
        self.clock = clock
        self.transport = transport
        self.environ = os.environ if environ is None else environ
        self.store = RepeaterBookStore.for_config(config)

    # -- configuration ----------------------------------------------------------
    def sources_config(self) -> SourcesConfig:
        return SourcesConfig.load(self.config.sources_config_path)

    def configure(
        self,
        *,
        enabled: Optional[bool] = None,
        token_env: Optional[str] = None,
        token_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Store the enable flag and *where* the token is, never the token."""
        cfg = self.sources_config()
        if enabled is not None:
            cfg.repeaterbook_enabled = bool(enabled)
        if token_env is not None:
            name = token_env.strip()
            if name.startswith((policy.TOKEN_PREFIX, policy.SHARED_TOKEN_PREFIX)):
                raise TokenError("give the environment variable's name, not the token")
            cfg.repeaterbook_token_env = name or None
        if token_file is not None:
            cfg.repeaterbook_token_file = (
                str(check_token_file_path(token_file, repo_root=_repo_root())) if token_file.strip() else None
            )
        self.config.ensure_dirs()
        cfg.save(self.config.sources_config_path)
        return self.status()

    def forget_token(self) -> Dict[str, Any]:
        """Drop the stored token location. Separate from Delete All; the
        environment variable or file itself is the user's to remove."""
        cfg = self.sources_config()
        cfg.repeaterbook_token_env = None
        cfg.repeaterbook_token_file = None
        self.config.ensure_dirs()
        cfg.save(self.config.sources_config_path)
        return self.status()

    def token(self) -> Optional[Token]:
        cfg = self.sources_config()
        return load_token(
            token_env=cfg.repeaterbook_token_env,
            token_file=cfg.repeaterbook_token_file,
            environ=self.environ,
            repo_root=_repo_root(),
        )

    # -- status -----------------------------------------------------------------
    def status(self) -> Dict[str, Any]:
        now = self.clock()
        self.store.purge(now)
        cfg = self.sources_config()
        token_error = None
        try:
            token = self.token()
        except TokenError as exc:
            token, token_error = None, str(exc)
        requests_used, blocks = 0, []
        if token is not None:
            requests_used = len(self.store.requests_since(token.fingerprint, now - policy.REQUEST_WINDOW))
            blocks = self.store.active_blocks(token.fingerprint, now)
        regions = []
        for region in policy.REGIONS.values():
            meta = self.store.latest_raw_meta(region.code)
            freshness = "none"
            if meta is not None:
                age = now - parse_iso(meta["fetched_at"])
                freshness = "fresh" if age < policy.RAW_FRESH else "stale"
            regions.append(
                {
                    "code": region.code,
                    "name": region.name,
                    "verified": region.verified,
                    "note": region.note,
                    "cache": freshness,
                    "last_fetch": meta["fetched_at"] if meta else None,
                }
            )
        ready = bool(cfg.repeaterbook_enabled and token is not None and not blocks)
        return {
            "enabled": cfg.repeaterbook_enabled,
            "token_configured": token is not None,
            "token_source": token.source if token is not None else None,
            "token_fingerprint": token.fingerprint if token is not None else None,
            "token_error": token_error,
            "ready": ready,
            "message": None if cfg.repeaterbook_enabled else policy.PENDING_APPROVAL_MESSAGE,
            "user_agent": policy.USER_AGENT,
            "requests_last_24h": requests_used,
            "requests_remaining_24h": max(0, policy.MAX_REQUESTS_PER_24H - requests_used),
            "blocks": blocks,
            "regions": regions,
            "staged_pending": len(self.store.staged()),
            "applied_records": len(self.store.derived()),
            "limits": {
                "max_regions_per_action": policy.MAX_REGIONS_PER_ACTION,
                "max_requests_per_24h": policy.MAX_REQUESTS_PER_24H,
                "region_cooldown_minutes": int(policy.REGION_COOLDOWN.total_seconds() // 60),
                "radius_mi": [policy.RADIUS_MIN_MI, policy.RADIUS_MAX_MI],
                "candidate_cap": policy.CANDIDATE_CAP,
            },
            "attribution": attribution(),
        }

    # -- refresh -------------------------------------------------------------------
    def _precheck(self, token: Token, regions: Sequence[policy.Region], now: datetime.datetime) -> None:
        for block in self.store.active_blocks(token.fingerprint, now):
            if block["kind"] == "auth":
                raise LimitError(
                    f"RepeaterBook refused this token earlier ({block['reason']}). Correct the cause, "
                    "then run 'wasds150 repeaterbook unblock'; nothing is retried automatically"
                )
            raise LimitError(f"RepeaterBook refresh is locked until {block['until']} after a rate-limit response")
        for region in regions:
            last = self.store.last_request(token.fingerprint, region.code)
            if last is not None and now - last < policy.REGION_COOLDOWN:
                raise LimitError(
                    f"{region.code} was requested at {iso(last)}; it may not be requested again "
                    f"before {iso(last + policy.REGION_COOLDOWN)}. Nothing was sent"
                )
        used = len(self.store.requests_since(token.fingerprint, now - policy.REQUEST_WINDOW))
        remaining = policy.MAX_REQUESTS_PER_24H - used
        if len(regions) > remaining:
            raise LimitError(
                f"this action needs {len(regions)} request(s) but only {max(remaining, 0)} of "
                f"{policy.MAX_REQUESTS_PER_24H} remain in the rolling 24 hours. Nothing was sent"
            )

    def refresh(self, request: RefreshRequest, *, offline: bool = False) -> Dict[str, Any]:
        """One explicit user action. ``offline`` re-filters the freshest cached
        responses (under 7 days old) without contacting RepeaterBook."""
        regions, spec = validate_request(request)
        now = self.clock()
        self.store.purge(now)
        if offline:
            per_region, sent = self._cached(regions, now), 0
        else:
            per_region = self._fetch(regions)
            sent = len(regions)
        result = filter_records(per_region, spec)
        if len(result.candidates) > policy.CANDIDATE_CAP:
            self.store.purge(self.clock())
            raise CandidateCapError(
                f"{len(result.candidates)} repeaters matched; the limit is {policy.CANDIDATE_CAP}, so "
                "nothing was imported. Reduce the radius or the bands"
            )
        action_id = uuid.uuid4().hex[:12]
        self.store.stage(action_id, result.candidates)
        self.store.purge(self.clock())
        return {
            "action_id": action_id,
            "regions": [region.code for region in regions],
            "requests_sent": sent,
            "offline": offline,
            "candidates": [self._present(c) for c in result.candidates],
            "drops": result.drop_summary(),
            "attribution": attribution(),
        }

    def _cached(self, regions: Sequence[policy.Region], now: datetime.datetime):
        per_region = []
        for region in regions:
            raw = self.store.latest_fresh_raw(region.code, now)
            if raw is None:
                raise PolicyError(f"no cached RepeaterBook response for {region.code} is under 7 days old")
            per_region.append((region.code, raw["fetched_at"], parse_export(raw["body"])))
        return per_region

    def _fetch(self, regions: Sequence[policy.Region]):
        cfg = self.sources_config()
        if not cfg.repeaterbook_enabled:
            raise NotEnabledError(policy.PENDING_APPROVAL_MESSAGE)
        token = self.token()
        if token is None:
            raise TokenMissingError(
                f"no RepeaterBook token is set; put your own rbuapp_ token in "
                f"{cfg.repeaterbook_token_env or policy.DEFAULT_TOKEN_ENV} or configure a token file"
            )
        client = RepeaterBookClient(token, transport=self.transport)
        fp = token.fingerprint
        per_region = []
        with self.store.action_lock(self.clock()):
            self._precheck(token, regions, self.clock())
            for region in regions:  # sequential, never parallel
                sent_at = self.clock()
                # Counted before sending: an attempt that dies in flight still spent budget.
                self.store.record_request(fp, region.code, sent_at)
                try:
                    body = client.export(region, now=sent_at)
                except RateLimited as exc:
                    wait = max(policy.RATE_LIMIT_LOCKOUT, exc.retry_after or datetime.timedelta(0))
                    self.store.set_block(fp, "rate-limit", sent_at + wait, str(exc))
                    self.store.ledger_add(fp, region.code, sent_at, exc.status, "rate-limited")
                    raise
                except AuthError as exc:
                    self.store.set_block(fp, "auth", None, str(exc))
                    self.store.ledger_add(fp, region.code, sent_at, exc.status, "auth-refused")
                    raise
                except RepeaterBookError as exc:
                    self.store.ledger_add(fp, region.code, sent_at, exc.status, type(exc).__name__)
                    raise
                # Nothing the server echoes may carry the token onto disk.
                body = body.replace(token.reveal().encode("utf-8"), b"***REDACTED***")
                self.store.put_raw(region.code, body, sent_at)
                self.store.ledger_add(fp, region.code, sent_at, 200, "ok")
                per_region.append((region.code, iso(sent_at), parse_export(body)))
        return per_region

    def unblock_auth(self) -> bool:
        """The operator's acknowledgement that an authentication error is fixed."""
        token = self.token()
        return bool(token and self.store.clear_block(token.fingerprint, "auth"))

    # -- review and apply ----------------------------------------------------------
    def _present(self, record: Dict[str, Any]) -> Dict[str, Any]:
        item = dict(record)
        item["detail_url"] = detail_url(record.get("state_id", ""), record.get("rb_id", ""))
        return item

    def staged(self, action_id: Optional[str] = None) -> Dict[str, Any]:
        now = self.clock()
        self.store.purge(now)
        action_id = action_id or self.store.latest_action_id()
        rows = self.store.staged(action_id) if action_id else []
        candidates = []
        for row in rows:
            item = self._present(row["record"])
            item["fresh"] = now - parse_iso(row["fetched_at"]) < policy.RAW_FRESH
            candidates.append(item)
        return {"action_id": action_id, "candidates": candidates, "attribution": attribution()}

    def apply(self, action_id: Optional[str] = None, *, include_flagged: bool = False) -> Dict[str, Any]:
        """Move reviewed candidates into the applied records. Stale (over 7
        days) and flagged (off-air, closed, no input) candidates stay out
        unless ``include_flagged``; stale ones stay out regardless."""
        now = self.clock()
        self.store.purge(now)
        action_id = action_id or self.store.latest_action_id()
        rows = self.store.staged(action_id) if action_id else []
        applied, skipped = [], []
        for row in rows:
            record = row["record"]
            if now - parse_iso(row["fetched_at"]) >= policy.RAW_FRESH:
                skipped.append({"rb_key": record["rb_key"], "reason": "older than 7 days; refresh again"})
                continue
            if record.get("flags") and not include_flagged:
                skipped.append({"rb_key": record["rb_key"], "reason": "flagged: " + ", ".join(record["flags"])})
                continue
            self.store.upsert_derived(
                record["rb_key"], record, retrieved_at=record["retrieved_at"], reviewed_at=iso(now)
            )
            applied.append(row["id"])
        self.store.mark_staged(applied, "applied")
        return {
            "action_id": action_id,
            "applied": len(applied),
            "skipped": skipped,
            "attribution": attribution(),
        }

    def records(self) -> Dict[str, Any]:
        self.store.purge(self.clock())
        return {"records": [self._present(r) for r in self.store.derived()], "attribution": attribution()}

    def reviewed_favorite(self):
        """The applied records as the local-only ``RB01`` Favorites List."""
        self.store.purge(self.clock())
        return favorite_from_records(self.store.derived())

    def register_export_report(self, path: Path) -> None:
        """Record a companion report that holds RepeaterBook-derived rows so
        retention and Delete All remove it too."""
        self.store.register_report(path, self.clock())

    # -- reports ----------------------------------------------------------------------
    def write_review_report(self, fmt: str = "md", out: Optional[Path] = None, action_id: Optional[str] = None) -> Path:
        if fmt not in ("md", "html"):
            raise PolicyError("report format must be md or html")
        staged = self.staged(action_id)
        text = render_review_markdown(staged) if fmt == "md" else render_review_html(staged)
        path = Path(out) if out else self.store.reports_dir / f"review-{staged['action_id'] or 'none'}.{fmt}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        self.store.register_report(path, self.clock())
        return path

    # -- retention and deletion ---------------------------------------------------------
    def purge(self) -> Dict[str, int]:
        return self.store.purge(self.clock())

    def delete_all(self) -> Dict[str, int]:
        """Delete All RepeaterBook Data. The token location is untouched."""
        return self.store.delete_all()


# -- presentation -------------------------------------------------------------------------
_COLUMNS = ("rb_key", "callsign", "output_mhz", "input_mhz", "tx_tone", "rx_tone", "city", "state", "distance_mi", "flags")


def _cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, list):
        return ", ".join(value) or "-"
    return str(value)


def format_preview(result: Dict[str, Any]) -> str:
    """The CLI's plain-text view of a refresh or a staged review."""
    lines = [ATTRIBUTION_LINE, ""]
    candidates = result.get("candidates", [])
    lines.append(f"{len(candidates)} candidate(s) staged for review (action {result.get('action_id')})")
    for c in candidates:
        tx = f"{c['input_mhz']:.4f}" if c.get("input_mhz") else "no input"
        lines.append(
            f"  {c['rb_key']:>10}  {c.get('callsign', ''):8} {c['output_mhz']:.4f} -> {tx:9} "
            f"tone {c.get('tx_tone') or '-':12} {c.get('distance_mi', '-'):>5} mi  {c.get('city', '')}"
            + (f"  [{', '.join(c['flags'])}]" if c.get("flags") else "")
        )
    drops = result.get("drops") or {}
    if drops:
        lines.append("Dropped:")
        lines.extend(f"  {reason}: {count}" for reason, count in drops.items())
    return "\n".join(lines) + "\n"


def render_review_markdown(staged: Dict[str, Any]) -> str:
    lines = [
        "# RepeaterBook review",
        "",
        "## Source and attribution",
        "",
        f"{ATTRIBUTION_MARKDOWN}. Local review copy for programming the operator's own radios; "
        "not for redistribution.",
        "",
        f"Action: {staged.get('action_id')}",
        "",
        "| " + " | ".join(_COLUMNS) + " | page |",
        "| " + " | ".join("---" for _ in _COLUMNS) + " | --- |",
    ]
    for c in staged.get("candidates", []):
        cells = [_cell(c.get(col)).replace("|", "/") for col in _COLUMNS]
        lines.append("| " + " | ".join(cells) + f" | [RepeaterBook]({c['detail_url']}) |")
    return "\n".join(lines) + "\n"


def render_review_html(staged: Dict[str, Any]) -> str:
    esc = html.escape
    rows = "".join(
        "<tr>" + "".join(f"<td>{esc(_cell(c.get(col)))}</td>" for col in _COLUMNS)
        + f"<td><a href=\"{esc(c['detail_url'])}\">RepeaterBook</a></td></tr>"
        for c in staged.get("candidates", [])
    )
    head = "".join(f"<th>{esc(col)}</th>" for col in _COLUMNS)
    return (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>RepeaterBook review</title></head><body>"
        "<h1>RepeaterBook review</h1><h2>Source and attribution</h2>"
        f"<p><a href=\"{esc(policy.ATTRIBUTION_URL)}\">{esc(policy.ATTRIBUTION_TEXT)}</a>. "
        "Local review copy for programming the operator's own radios; not for redistribution.</p>"
        f"<p>Action: {esc(str(staged.get('action_id')))}</p>"
        f"<table><thead><tr>{head}<th>page</th></tr></thead><tbody>{rows}</tbody></table></body></html>\n"
    )
