"""JSON API handlers, mirroring the CLI 1:1 (see ``wasds150/cli.py``).

Every handler is a plain function of ``(ctx, request)`` so the same logic
that backs the CLI subcommands (:mod:`wasds150.generate.pipeline`,
:mod:`wasds150.diffing.differ`, :mod:`wasds150.history.snapshots`, ...) is
reused verbatim rather than re-implemented for the web UI.
"""
from __future__ import annotations

import base64
import re
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

from wasds150.appctx import AppContext
from wasds150.bundle.csv_export import export_csv
from wasds150.bundle.generate_outputs import generate_outputs
from wasds150.bundle.hpe_export import build_per_list_hpe
from wasds150.bundle.markdown_export import export_markdown
from wasds150.bundle.sentinel_import_pack import build_sentinel_import_pack
from wasds150.catalog import loader as catalog_loader
from wasds150.catalog.ids import slugify, stable_id
from wasds150.catalog.validate import validate_catalog
from wasds150.diffing.differ import diff_profile
from wasds150.generate.pipeline import apply_profile
from wasds150.history.rollback import rollback_profile
from wasds150.history.snapshots import SnapshotStore
from wasds150.hpe import builders as hpe_builders
from wasds150.hpe import codec as hpe_codec
from wasds150.hpe import hpdb as hpe_hpdb
from wasds150.hpe import schema as hpe_schema
from wasds150.hpe import tree as hpe_tree
from wasds150.hpe.record import parse_records, serialize_records
from wasds150.hpe.validation import (
    HpeValidationError,
    require_valid_document,
    require_valid_hpe_container,
    validate_document,
    validate_systems,
)
from wasds150.installer import detect as installer_detect
from wasds150.installer import hpdb_reader as installer_hpdb_reader
from wasds150.installer.backup import InstallerError, backup_card, verify_backup
from wasds150.installer.rollback import rollback_from_backup
from wasds150.installer.writer import write_favorites_list
from wasds150.merge.three_way import apply_merge, three_way_merge
from wasds150.models.catalog import ORIGIN_LOCAL, FavoritesList, System
from wasds150.models.profile import EDITABLE_FIELDS
from wasds150.webui.router import Response, RequestContext, Router


def _error(status: int, message: str) -> Response:
    return Response.json(status, {"error": message})


def get_dashboard(ctx: AppContext, req: RequestContext) -> Response:
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)
    changes = diff_profile(ctx.catalog, profile)
    store = SnapshotStore(ctx.config.history_dir)
    latest = store.latest()
    return Response.json(
        200,
        {
            "catalog_source": ctx.catalog_source,
            "counts": result.counts,
            "content_hash": result.content_hash,
            "warnings": result.warnings,
            "pending_changes": len(changes),
            "latest_snapshot": latest.__dict__ if latest else None,
        },
    )


def _safe_source_reference(value: Any) -> Any:
    if not isinstance(value, str) or not value:
        return value
    try:
        parsed = urllib.parse.urlsplit(value)
    except ValueError:
        return "(invalid source reference redacted)"
    if parsed.scheme in ("http", "https"):
        hostname = parsed.hostname or ""
        netloc = hostname
        try:
            if parsed.port is not None:
                netloc = f"{netloc}:{parsed.port}"
        except ValueError:
            return "(invalid source reference redacted)"
        return urllib.parse.urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
    if parsed.scheme == "catalog" and re.fullmatch(r"catalog://FL\d+[A-Za-z]?", value):
        return value
    if parsed.scheme == "file" or value.startswith(("/", "\\")) or (len(value) > 2 and value[1:3] in (":\\", ":/")):
        return "(local path redacted)"
    if parsed.scheme:
        return "(unsupported source reference redacted)"
    return value


def _profile_state(profile, fl: FavoritesList, *, include_overrides: bool = False) -> Dict[str, Any]:
    entry = profile.entries.get(fl.slug)
    enabled_override = entry.enabled if entry is not None else None
    removed = entry.removed if entry is not None else False
    effective_enabled = False if removed else (
        enabled_override if enabled_override is not None else fl.enabled
    )
    overrides = dict(entry.overrides) if entry is not None else {}
    state = {
        "removed": removed,
        "enabled_override": enabled_override,
        "effective_enabled": effective_enabled,
        "override_fields": sorted(overrides),
        "note_present": bool(entry.note) if entry is not None else False,
        "origin": fl.origin,
        "is_local": fl.origin == ORIGIN_LOCAL,
    }
    if include_overrides:
        state["overrides"] = {
            key: (
                "(private override value hidden)"
                if key == "notes"
                else _safe_source_reference(value) if key == "source_url" else value
            )
            for key, value in overrides.items()
        }
    return state


def _catalog_detail(fl: FavoritesList, profile) -> Dict[str, Any]:
    data = fl.to_dict()
    data["source_url"] = _safe_source_reference(data.get("source_url"))
    for item in data.get("provenance", []):
        item["source_url"] = _safe_source_reference(item.get("source_url"))
    data["profile_state"] = _profile_state(profile, fl, include_overrides=True)
    return data


def _catalog_summary(fl: FavoritesList, profile) -> Dict[str, Any]:
    sites = [site for system in fl.systems for site in system.sites]
    departments = [department for system in fl.systems for department in system.departments]
    departments.extend(department for site in sites for department in site.departments)
    return {
        "slug": fl.slug,
        "favorite_key": fl.favorite_key,
        "favorite_name": fl.favorite_name,
        "region": fl.region,
        "scenario": fl.scenario,
        "mode": fl.mode,
        "origin": fl.origin,
        "system_count": len(fl.systems),
        "site_count": len(sites),
        "department_count": len(departments),
        "channel_count": sum(len(department.channels) for department in departments),
        "trunk_frequency_count": sum(len(system.trunk_frequencies) for system in fl.systems),
        "provenance_count": len(fl.provenance),
        "profile_state": _profile_state(profile, fl),
    }


def get_catalog(ctx: AppContext, req: RequestContext) -> Response:
    favorites = ctx.catalog.favorites
    profile = ctx.load_profile()
    region = (req.query.get("region") or [None])[0]
    if region:
        favorites = [fl for fl in favorites if region.lower() in fl.region.lower()]
    return Response.json(200, {"favorites": [_catalog_detail(fl, profile) for fl in favorites]})


def get_catalog_summaries(ctx: AppContext, req: RequestContext) -> Response:
    favorites = ctx.catalog.favorites
    profile = ctx.load_profile()
    region = (req.query.get("region") or [None])[0]
    if region:
        favorites = [fl for fl in favorites if region.lower() in fl.region.lower()]
    return Response.json(200, {
        "favorites": [_catalog_summary(fl, profile) for fl in favorites],
        "total": len(favorites),
    })


def get_catalog_entry(ctx: AppContext, req: RequestContext) -> Response:
    slug = req.params["slug"].lower()
    fl = ctx.catalog.by_slug(slug)
    if fl is None:
        return _error(404, f"Unknown baseline slug: {slug}")
    return Response.json(200, _catalog_detail(fl, ctx.load_profile()))


def get_profile(ctx: AppContext, req: RequestContext) -> Response:
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)
    return Response.json(
        200,
        {
            "favorites": [fl.to_dict() for fl in result.favorites],
            "counts": result.counts,
            "content_hash": result.content_hash,
            "warnings": result.warnings,
            "overridden_slugs": sorted(profile.entries.keys()),
            "local_slugs": sorted(profile.local_lists.keys()),
        },
    )


def get_preview(ctx: AppContext, req: RequestContext) -> Response:
    profile = ctx.load_profile()
    try:
        result = apply_profile(ctx.catalog, profile)
    except ValueError as exc:
        return _error(422, str(exc))
    changes = diff_profile(ctx.catalog, profile)
    return Response.json(
        200,
        {
            "counts": result.counts,
            "content_hash": result.content_hash,
            "warnings": result.warnings,
            "changes": [c.to_dict() for c in changes],
        },
    )


def _resolve_slug(ctx: AppContext, profile, raw_slug: str):
    slug = (raw_slug or "").strip().lower()
    if ctx.catalog.by_slug(slug) is not None or slug in profile.local_lists:
        return slug
    return None


def post_profile_enable(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    profile = ctx.load_profile()
    slug = _resolve_slug(ctx, profile, body.get("slug", ""))
    if slug is None:
        return _error(404, f"Unknown slug: {body.get('slug')!r}")
    enabled = bool(body.get("enabled", True))
    if slug in profile.local_lists:
        profile.local_lists[slug].enabled = enabled
    else:
        profile.set_enabled(slug, enabled)
    ctx.save_profile(profile)
    return Response.json(200, {"slug": slug, "enabled": enabled})


def post_profile_edit(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    profile = ctx.load_profile()
    slug = _resolve_slug(ctx, profile, body.get("slug", ""))
    if slug is None:
        return _error(404, f"Unknown slug: {body.get('slug')!r}")
    field_name = body.get("field")
    if field_name not in EDITABLE_FIELDS:
        return _error(400, f"Field {field_name!r} is not editable; choices: {EDITABLE_FIELDS}")
    value = body.get("value")
    if field_name == "flqk" and value is not None:
        value = int(value)
    if slug in profile.local_lists:
        setattr(profile.local_lists[slug], field_name, value)
    else:
        profile.set_override(slug, field_name, value)
    ctx.save_profile(profile)
    return Response.json(200, {"slug": slug, "field": field_name, "value": value})


def post_profile_remove(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    profile = ctx.load_profile()
    slug = _resolve_slug(ctx, profile, body.get("slug", ""))
    if slug is None:
        return _error(404, f"Unknown slug: {body.get('slug')!r}")
    if slug in profile.local_lists:
        profile.remove_local_list(slug)
    else:
        profile.set_removed(slug, True)
        reason = body.get("reason")
        if reason:
            profile.entry_for(slug).note = reason
    ctx.save_profile(profile)
    return Response.json(200, {"slug": slug, "removed": True})


def post_profile_restore(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    slug = (body.get("slug") or "").strip().lower()
    profile = ctx.load_profile()
    if slug in profile.local_lists:
        return _error(400, "local lists cannot be restored; remove them instead")
    profile.restore(slug)
    ctx.save_profile(profile)
    return Response.json(200, {"slug": slug, "restored": True})


_LOCAL_FIELDS = (
    "favorite_name",
    "region",
    "counties",
    "scenario",
    "source_type",
    "system_or_category",
    "sites_or_coverage",
    "departments_or_channels",
    "mode",
    "monitorability",
    "upgrade_required",
    "source_url",
    "notes",
)


def post_profile_local_add(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    key = body.get("key")
    if not key:
        return _error(400, "'key' is required")
    slug = slugify(key)
    profile = ctx.load_profile()
    if ctx.catalog.by_slug(slug) is not None:
        return _error(409, f"{slug!r} collides with a baseline entry")
    if slug in profile.local_lists:
        return _error(409, f"local list {slug!r} already exists")

    kwargs: Dict[str, Any] = {name: body.get(name, "") for name in _LOCAL_FIELDS}
    fl = FavoritesList(
        id=stable_id(slug),
        slug=slug,
        favorite_key=key,
        enabled=bool(body.get("enabled", True)),
        flqk=body.get("flqk"),
        origin=ORIGIN_LOCAL,
        **kwargs,
    )
    profile.add_local_list(fl)
    ctx.save_profile(profile)
    return Response.json(201, fl.to_dict())


def delete_profile_local(ctx: AppContext, req: RequestContext) -> Response:
    slug = req.params["slug"].lower()
    profile = ctx.load_profile()
    if slug not in profile.local_lists:
        return _error(404, f"No local list {slug!r}")
    profile.remove_local_list(slug)
    ctx.save_profile(profile)
    return Response.json(200, {"slug": slug, "deleted": True})


def post_generate(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    profile = ctx.load_profile()
    try:
        result = apply_profile(ctx.catalog, profile)
    except ValueError as exc:
        return _error(422, str(exc))

    out_dir = Path(body.get("out") or (ctx.config.state_dir / "generated"))
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = body.get("formats") or ["csv", "md", "zip", "hpe"]
    try:
        published = generate_outputs(result, out_dir, formats)
    except (HpeValidationError, OSError) as exc:
        return _error(422, str(exc))
    except ValueError as exc:
        return _error(400, str(exc))

    store = SnapshotStore(ctx.config.history_dir)
    snap = store.commit(profile, result, message=body.get("message", ""))
    return Response.json(
        200,
        {
            "snapshot_id": snap.id,
            "content_hash": result.content_hash,
            "counts": result.counts,
            "warnings": list(result.warnings) + published.warnings,
            "files": [str(path) for path in published.files],
        },
    )


def get_generate_hpe_list(ctx: AppContext, req: RequestContext) -> Response:
    """Download exactly one Favorites List's ``.hpe``, built fresh from
    the current profile+catalog (no snapshot needed) — the single-file
    complement to the ``zip`` bundle's ``hpe/`` directory, for a quick
    "just this one" download from the web UI."""
    slug = req.params["slug"].strip().lower()
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)
    fl = next((f for f in result.favorites if f.slug == slug), None)
    if fl is None:
        return _error(404, f"Unknown slug: {slug}")
    export = build_per_list_hpe([fl])
    if not export.files:
        return _error(409, "; ".join(export.warnings) or f"{slug}: no structured systems available")
    (filename, hpe_bytes), = export.files.items()
    return Response(
        status=200,
        body=hpe_bytes,
        content_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def get_history(ctx: AppContext, req: RequestContext) -> Response:
    store = SnapshotStore(ctx.config.history_dir)
    return Response.json(200, {"snapshots": [s.__dict__ for s in store.list()]})


def get_history_entry(ctx: AppContext, req: RequestContext) -> Response:
    store = SnapshotStore(ctx.config.history_dir)
    try:
        data = store.load_raw(req.params["id"])
    except KeyError:
        return _error(404, f"No such snapshot: {req.params['id']!r}")
    return Response.json(200, data)


def post_history_rollback(ctx: AppContext, req: RequestContext) -> Response:
    snap_id = req.params["id"]
    store = SnapshotStore(ctx.config.history_dir)
    try:
        store.load_raw(snap_id)
    except KeyError:
        return _error(404, f"No such snapshot: {snap_id!r}")
    path = rollback_profile(ctx.config.profile_path, ctx.config.history_dir, snap_id)
    return Response.json(200, {"restored_to": snap_id, "profile_path": str(path)})


_EXPORT_CONTENT_TYPES = {
    "csv": "text/csv",
    "md": "text/markdown",
    "zip": "application/zip",
}


def get_export(ctx: AppContext, req: RequestContext) -> Response:
    fmt = req.params["format"].lower()
    if fmt not in _EXPORT_CONTENT_TYPES:
        return _error(400, f"Unknown export format {fmt!r}; choices: {sorted(_EXPORT_CONTENT_TYPES)}")
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)

    with tempfile.TemporaryDirectory(prefix="wasds150-export-") as tmp:
        base = Path(tmp)
        if fmt == "csv":
            path = export_csv(result.enabled_favorites, base / "favorites.csv")
        elif fmt == "md":
            path = export_markdown(result.enabled_favorites, base / "favorites-overview.md")
        else:
            path = build_sentinel_import_pack(result, base / "sentinel-import-pack.zip")
        data = path.read_bytes()

    return Response(
        status=200,
        body=data,
        content_type=_EXPORT_CONTENT_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="{path.name}"'},
    )


def get_sources(ctx: AppContext, req: RequestContext) -> Response:
    from wasds150.sources.base import OnlineSourceAdapter
    from wasds150.sources.registry import list_sources

    sources = list_sources()
    return Response.json(
        200,
        {
            "sources": [
                {
                    "name": name,
                    "available": cls.available,
                    "kind": getattr(cls, "kind", None) if issubclass(cls, OnlineSourceAdapter) else "legacy",
                }
                for name, cls in sorted(sources.items())
            ]
        },
    )


def get_sources_status(ctx: AppContext, req: RequestContext) -> Response:
    from wasds150.cache.store import HttpCacheStore
    from wasds150.sources.config import SourcesConfig
    from wasds150.sources.registry import list_sources

    sources_config = SourcesConfig.load(ctx.config.sources_config_path)
    store = HttpCacheStore(ctx.config.cache_dir)
    rows = []
    for name in sorted(list_sources()):
        entries = store.entries_for_source(name)
        rows.append(
            {
                "name": name,
                "cached_urls": len(entries),
                "most_recent_fetch": max((e.fetched_at for e in entries), default=None),
            }
        )
    return Response.json(200, {"offline": sources_config.offline, "sources": rows})


def post_sources_configure(ctx: AppContext, req: RequestContext) -> Response:
    from wasds150.sources.config import SourcesConfig

    body = req.json_body() or {}
    ctx.config.ensure_dirs()
    sources_config = SourcesConfig.load(ctx.config.sources_config_path)
    if "offline" in body:
        sources_config.offline = bool(body["offline"])
    if "sentinel_local_mount" in body:
        sources_config.sentinel_local_mount = body["sentinel_local_mount"] or None
        sources_config.sentinel_local_hpdb_cfg = None
    if "sentinel_local_hpdb_cfg" in body:
        sources_config.sentinel_local_hpdb_cfg = body["sentinel_local_hpdb_cfg"] or None
        sources_config.sentinel_local_mount = None
    if "radioreference_export_path" in body:
        sources_config.radioreference_export_path = body["radioreference_export_path"] or None
    if "radioreference_username" in body:
        sources_config.radioreference_username = body["radioreference_username"] or None
    if "radioreference_app_key" in body:
        sources_config.radioreference_app_key = body["radioreference_app_key"] or None
    sources_config.save(ctx.config.sources_config_path)
    # Never echo credential-like values back in the response body.
    return Response.json(
        200,
        {
            "offline": sources_config.offline,
            "sentinel_local_configured": bool(
                sources_config.sentinel_local_mount or sources_config.sentinel_local_hpdb_cfg
            ),
            "radioreference_configured": bool(
                sources_config.radioreference_export_path
                or (sources_config.radioreference_username and sources_config.radioreference_app_key)
            ),
        },
    )


def _instantiate_source_for_ui(name: str, sources_config):
    from wasds150.sources.base import OnlineSourceAdapter
    from wasds150.sources.radioreference_premium import RadioReferenceCredentials, RadioReferencePremiumSource
    from wasds150.sources.registry import get_source_class
    from wasds150.sources.sentinel_local import SentinelLocalSource

    cls = get_source_class(name)
    if not issubclass(cls, OnlineSourceAdapter):
        return None
    if name == "sentinel_local":
        if sources_config.sentinel_local_mount:
            return SentinelLocalSource(mount_point=Path(sources_config.sentinel_local_mount))
        if sources_config.sentinel_local_hpdb_cfg:
            return SentinelLocalSource(hpdb_cfg_path=Path(sources_config.sentinel_local_hpdb_cfg))
        return None
    if name == "radioreference_premium":
        if sources_config.radioreference_export_path:
            return RadioReferencePremiumSource(export_path=Path(sources_config.radioreference_export_path))
        if sources_config.radioreference_username and sources_config.radioreference_app_key:
            return RadioReferencePremiumSource(
                credentials=RadioReferenceCredentials(
                    username=sources_config.radioreference_username,
                    app_key=sources_config.radioreference_app_key,
                )
            )
        return None
    return cls()


def post_sources_fetch(ctx: AppContext, req: RequestContext) -> Response:
    from wasds150.cache.http import CachedHttpClient
    from wasds150.cache.store import HttpCacheStore
    from wasds150.sources.config import SourcesConfig
    from wasds150.update.pipeline import run_sources

    body = req.json_body() or {}
    name = body.get("name")
    if not name:
        return _error(400, "'name' is required")
    sources_config = SourcesConfig.load(ctx.config.sources_config_path)
    try:
        source = _instantiate_source_for_ui(name, sources_config)
    except KeyError as exc:
        return _error(404, str(exc))
    if source is None:
        return _error(400, f"source {name!r} is not configured/runnable (see Sources -> Configure)")

    http_client = (
        CachedHttpClient(HttpCacheStore(ctx.config.cache_dir), offline=sources_config.offline)
        if source.kind != "local"
        else None
    )
    run = run_sources([source], http_client=http_client)
    outcome = run.outcomes[0]
    return Response.json(200 if outcome.ok else 502, {"outcome": outcome.to_dict()})


def post_sources_update(ctx: AppContext, req: RequestContext) -> Response:
    from wasds150.cache.http import CachedHttpClient
    from wasds150.cache.store import HttpCacheStore
    from wasds150.sources.base import OnlineSourceAdapter
    from wasds150.sources.config import SourcesConfig
    from wasds150.sources.registry import list_sources
    from wasds150.update.pipeline import build_and_merge, run_sources

    body = req.json_body() or {}
    sources_config = SourcesConfig.load(ctx.config.sources_config_path)
    offline = sources_config.offline or bool(body.get("offline", False))
    only = set(body["only"]) if body.get("only") else None

    instances = []
    for name, cls in list_sources().items():
        if not issubclass(cls, OnlineSourceAdapter) or not cls.available:
            continue
        if only is not None and name not in only:
            continue
        instance = _instantiate_source_for_ui(name, sources_config)
        if instance is not None:
            instances.append(instance)

    http_client = CachedHttpClient(HttpCacheStore(ctx.config.cache_dir), offline=offline)
    run = run_sources(instances, http_client=http_client)
    profile = ctx.load_profile()
    built = build_and_merge(ctx.catalog, profile, run.facts)
    merge_result = built["merge"]
    coverage = built["coverage"]

    applied = False
    if body.get("apply"):
        force = bool(body.get("force", False))
        if merge_result.conflicts and not force:
            return Response.json(
                409,
                {
                    "error": f"{len(merge_result.conflicts)} conflict(s) found; pass force=true to apply anyway",
                    "run": run.to_dict(),
                    "coverage": [c.to_dict() for c in coverage],
                    "merge": merge_result.to_dict(),
                },
            )
        new_profile = apply_merge(profile, merge_result)
        ctx.save_catalog(merge_result.merged_catalog)
        ctx.save_profile(new_profile)
        applied = True

    return Response.json(
        200,
        {
            "run": run.to_dict(),
            "coverage": [c.to_dict() for c in coverage],
            "merge": merge_result.to_dict(),
            "applied": applied,
        },
    )


def get_sources_provenance(ctx: AppContext, req: RequestContext) -> Response:
    slug = req.params["slug"].lower()
    fl = ctx.catalog.by_slug(slug)
    if fl is None:
        return _error(404, f"no such favorite: {slug}")
    return Response.json(200, {"slug": fl.slug, "provenance": [p.to_dict() for p in fl.provenance]})


# --------------------------------------------------------------- hpe -------
def _hpe_text_from_body(body: Dict[str, Any]) -> str:
    """Accept either raw base64 file content (browser file-picker flow) or a
    server-side path (CLI-parity/testing flow)."""
    if body.get("content_base64"):
        data = base64.b64decode(body["content_base64"])
        if len(data) >= 2 and data[0] == (0x1F ^ hpe_codec.XOR_KEY) and data[1] == (0x8B ^ hpe_codec.XOR_KEY):
            return hpe_codec.decode_container(data)
        return data.decode("ascii")
    if body.get("path"):
        path = Path(body["path"])
        data = path.read_bytes()
        if len(data) >= 2 and data[0] == (0x1F ^ hpe_codec.XOR_KEY) and data[1] == (0x8B ^ hpe_codec.XOR_KEY):
            return hpe_codec.decode_container(data)
        return data.decode("ascii")
    raise ValueError("either 'content_base64' or 'path' is required")


def post_hpe_inspect(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    try:
        text = _hpe_text_from_body(body)
    except (ValueError, hpe_codec.HpeError, OSError) as exc:
        return _error(400, str(exc))
    doc = parse_records(text)
    dialect = hpe_schema.detect_dialect(doc)
    nodes = hpe_tree.build_tree(doc)
    tag_counts: Dict[str, int] = {}
    for r in doc.records:
        tag_counts[r.tag] = tag_counts.get(r.tag, 0) + 1
    return Response.json(
        200,
        {
            "dialect": {"target_model": dialect.target_model, "format_version": dialect.format_version}
            if dialect
            else None,
            "has_signature_line": hpe_codec.has_signature_line(text),
            "record_count": len(doc.records),
            "tag_counts": tag_counts,
            "tree": hpe_tree.render_tree(nodes),
        },
    )


def post_hpe_validate(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    try:
        text = _hpe_text_from_body(body)
    except (ValueError, hpe_codec.HpeError, OSError) as exc:
        return _error(400, str(exc))
    doc = parse_records(text)
    dialect = hpe_schema.detect_dialect(doc)
    semantic_issues = validate_document(doc) if dialect and dialect.is_bcdx36hp else []
    issues = [str(issue) for issue in semantic_issues] or hpe_schema.validate_schema(doc, dialect)
    return Response.json(200, {"issues": issues, "dialect": dialect.target_model if dialect else None})


def post_hpe_build(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    raw_systems = body.get("systems")
    if raw_systems is None:
        return _error(400, "'systems' is required")
    try:
        systems = [System.from_dict(s) for s in raw_systems]
        doc = hpe_builders.build_favorites_document(systems)
    except (KeyError, TypeError, ValueError) as exc:
        return _error(400, f"invalid system definition: {exc}")
    model_issues = validate_systems(systems)
    if model_issues:
        return _error(422, "; ".join(str(issue) for issue in model_issues))
    try:
        require_valid_document(doc)
    except HpeValidationError as exc:
        return _error(422, str(exc))
    hpe_bytes = hpe_codec.encode_container(serialize_records(doc))
    try:
        require_valid_hpe_container(hpe_bytes)
    except HpeValidationError as exc:
        return _error(422, str(exc))
    return Response.json(
        200,
        {
            "issues": [],
            "record_count": len(doc.records),
            "hpe_content_base64": base64.b64encode(hpe_bytes).decode("ascii"),
        },
    )


# -------------------------------------------------------------- hpdb -------
def _load_hpdb_doc_from_body(body: Dict[str, Any]):
    if body.get("content_base64"):
        text = base64.b64decode(body["content_base64"]).decode("ascii")
    elif body.get("path"):
        text = Path(body["path"]).read_bytes().decode("ascii")
    else:
        raise ValueError("either 'content_base64' or 'path' is required")
    doc = parse_records(text)
    is_index = doc.find_first("StateInfo") is not None or doc.find_first("CountyInfo") is not None
    return doc, ("hpdb_index" if is_index else "hpdb_state")


def post_hpdb_inspect(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    try:
        doc, kind = _load_hpdb_doc_from_body(body)
    except (ValueError, OSError) as exc:
        return _error(400, str(exc))

    if kind == "hpdb_index":
        index = hpe_hpdb.CountyIndex.from_hpdb_cfg(doc)
        return Response.json(
            200,
            {
                "kind": kind,
                "states": index.state_by_id,
                "counties": [
                    {"id": cid, "name": name, "state_id": index.county_state.get(cid)}
                    for cid, name in index.by_id.items()
                ],
            },
        )

    systems = hpe_hpdb.segment_systems(doc)
    return Response.json(
        200,
        {
            "kind": kind,
            "systems": [
                {
                    "kind": s.kind(),
                    "name": s.name(),
                    "tech": s.tech(),
                    "identity": list(s.identity()) if s.identity() else None,
                    "county_ids": s.county_ids(),
                    "state_ids": s.state_ids(),
                    "geo_count": len(s.geos()),
                }
                for s in systems
            ],
        },
    )


def post_hpdb_extract(ctx: AppContext, req: RequestContext) -> Response:
    from wasds150.hpe.record import new_document

    body = req.json_body() or {}
    try:
        doc, kind = _load_hpdb_doc_from_body(body)
    except (ValueError, OSError) as exc:
        return _error(400, str(exc))
    if kind != "hpdb_state":
        return _error(400, "extraction requires a s_<state>.hpd system file, not hpdb.cfg")

    systems = hpe_hpdb.segment_systems(doc)
    county_id = body.get("county_id")
    if county_id is not None:
        systems = hpe_hpdb.by_county(systems, int(county_id))
    within = body.get("within")  # {"lat":..,"lon":..,"radius_mi":..}
    if within:
        systems = hpe_hpdb.within_radius(systems, float(within["lat"]), float(within["lon"]), float(within["radius_mi"]))

    if not systems:
        return _error(404, "no systems matched the given filter(s)")

    preamble = [r for r in hpe_hpdb.preamble_records(doc) if r.tag in ("TargetModel", "FormatVersion")]
    records = list(preamble)
    for s in systems:
        records.extend(s.records)
    subset_doc = new_document(records, line_ending="\r\n")
    fav_doc = hpe_hpdb.to_favorites_dialect(subset_doc, synthesize_dqks=not body.get("no_dqks", False))
    if fav_doc.find_first("File") is None:
        from wasds150.hpe.record import Record

        fav_doc.records.append(Record(tag="File", fields=["HomePatrol Export File"]))
        fav_doc.line_endings.append("\r\n")

    try:
        require_valid_document(fav_doc, context="HPDB extraction")
    except HpeValidationError as exc:
        return _error(422, str(exc))
    hpe_bytes = hpe_codec.encode_container(serialize_records(fav_doc))
    try:
        require_valid_hpe_container(hpe_bytes, context="HPDB extraction")
    except HpeValidationError as exc:
        return _error(422, str(exc))
    return Response.json(
        200,
        {
            "matched_systems": [s.name() for s in systems],
            "hpe_content_base64": base64.b64encode(hpe_bytes).decode("ascii"),
        },
    )


def get_install_hpdb_inspect(ctx: AppContext, req: RequestContext) -> Response:
    mount = (req.query.get("mount") or [None])[0]
    if not mount:
        return _error(400, "'mount' query parameter is required")
    mount_path = Path(mount)
    if not installer_hpdb_reader.has_hpdb(mount_path):
        return _error(404, f"no HPDB/hpdb.cfg found under {mount_path}")
    card = installer_hpdb_reader.read_card_hpdb(mount_path)
    return Response.json(
        200,
        {
            "states": card.county_index.state_by_id if card.county_index else {},
            "counties": (
                [{"id": cid, "name": name} for cid, name in card.county_index.by_id.items()]
                if card.county_index
                else []
            ),
            "state_files": {
                str(state_id): [s.name() for s in hpe_hpdb.segment_systems(state_doc)]
                for state_id, state_doc in card.state_files.items()
            },
        },
    )


# --------------------------------------------------------------- merge -----
def _load_upstream_catalog(path_str: str):
    path = Path(path_str)
    if path.suffix.lower() == ".json":
        return catalog_loader.load_json(path)
    return catalog_loader.load_csv(path)


def post_merge_preview(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    upstream_path = body.get("upstream_path")
    if not upstream_path:
        return _error(400, "'upstream_path' is required")
    try:
        upstream = _load_upstream_catalog(upstream_path)
    except (OSError, ValueError) as exc:
        return _error(400, f"could not load upstream catalog: {exc}")
    profile = ctx.load_profile()
    result = three_way_merge(ctx.catalog, upstream, profile)
    return Response.json(200, result.to_dict())


def post_merge_apply(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    upstream_path = body.get("upstream_path")
    if not upstream_path:
        return _error(400, "'upstream_path' is required")
    try:
        upstream = _load_upstream_catalog(upstream_path)
    except (OSError, ValueError) as exc:
        return _error(400, f"could not load upstream catalog: {exc}")
    profile = ctx.load_profile()
    result = three_way_merge(ctx.catalog, upstream, profile)
    force = bool(body.get("force", False))
    if result.conflicts and not force:
        return Response.json(
            409,
            {
                "error": f"{len(result.conflicts)} conflict(s) found; pass force=true to apply anyway",
                **result.to_dict(),
            },
        )
    new_profile = apply_merge(profile, result)
    ctx.save_catalog(result.merged_catalog)
    ctx.save_profile(new_profile)
    return Response.json(
        200,
        {
            "merged_catalog_hash": result.merged_catalog.content_hash(),
            "changes": len(result.changes),
            "conflicts": len(result.conflicts),
        },
    )


# ------------------------------------------------------------- install -----
def get_install_detect(ctx: AppContext, req: RequestContext) -> Response:
    dirs = req.query.get("dir")
    candidate_dirs = [Path(d) for d in dirs] if dirs else None
    volumes = installer_detect.detect_volumes(candidate_dirs)
    return Response.json(
        200,
        {
            "volumes": [
                {"mount_point": str(v.mount_point), "label": v.label, "is_sds150_candidate": v.is_sds150_candidate}
                for v in volumes
            ]
        },
    )


def post_install_backup(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    mount = body.get("mount")
    out_dir = body.get("out_dir")
    if not mount or not out_dir:
        return _error(400, "'mount' and 'out_dir' are required")
    try:
        path = backup_card(Path(mount), Path(out_dir))
    except InstallerError as exc:
        return _error(400, str(exc))
    issues = verify_backup(path)
    return Response.json(200, {"backup_path": str(path), "verify_issues": issues})


def post_install_write(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    required = ("mount", "index", "backup_dir")
    missing = [k for k in required if body.get(k) is None]
    if missing:
        return _error(400, f"missing required field(s): {missing}")
    if bool(body.get("slug")) == bool(body.get("systems") is not None):
        return _error(400, "pass exactly one of 'slug' (generated Favorites List) or 'systems' (raw, advanced/debug)")

    if body.get("slug"):
        profile = ctx.load_profile()
        result = apply_profile(ctx.catalog, profile)
        slug = str(body["slug"]).strip().lower()
        fl = next((f for f in result.favorites if f.slug == slug), None)
        if fl is None:
            return _error(404, f"no such generated Favorites List: {body['slug']!r}")
        if not fl.systems:
            return _error(
                409,
                f"{fl.favorite_key} ({fl.favorite_name}) has no structured systems yet -- configure/update "
                "sources for local HPDB/RadioReference Premium data, or use 'systems' for a hand-authored entry.",
            )
        systems = fl.systems
        user_name = body.get("user_name") or fl.favorite_name
    else:
        try:
            systems = [System.from_dict(s) for s in body["systems"]]
        except (KeyError, TypeError, ValueError) as exc:
            return _error(400, f"invalid system definition: {exc}")
        user_name = body.get("user_name")
        if not user_name:
            return _error(400, "'user_name' is required when using 'systems' (no generated Favorites List to default it from)")

    try:
        doc = hpe_builders.build_favorites_document(systems)
    except (KeyError, TypeError, ValueError) as exc:
        return _error(400, f"invalid system definition: {exc}")

    execute = bool(body.get("execute", False))
    try:
        result = write_favorites_list(
            Path(body["mount"]),
            index=int(body["index"]),
            document=doc,
            user_name=user_name,
            backup_dir=Path(body["backup_dir"]),
            confirm_phrase=body.get("confirm"),
            dry_run=not execute,
        )
    except InstallerError as exc:
        return _error(400, str(exc))

    return Response.json(
        200,
        {
            "dry_run": result.dry_run,
            "planned_writes": result.planned_writes,
            "planned_deletes": result.planned_deletes,
            "backup_path": str(result.backup_path) if result.backup_path else None,
            "written_files": result.written_files,
            "deleted_files": result.deleted_files,
            "verified": result.verified,
            "warnings": result.warnings,
        },
    )


def post_install_rollback(ctx: AppContext, req: RequestContext) -> Response:
    body = req.json_body() or {}
    mount = body.get("mount")
    backup_path = body.get("backup")
    if not mount or not backup_path:
        return _error(400, "'mount' and 'backup' are required")
    try:
        restored = rollback_from_backup(Path(mount), Path(backup_path))
    except (InstallerError, ValueError) as exc:
        return _error(400, str(exc))
    return Response.json(200, {"restored": restored})


def build_router(ctx: AppContext) -> Router:
    router = Router()
    router.add("GET", "/api/v1/dashboard", lambda req: get_dashboard(ctx, req))
    router.add("GET", "/api/v1/catalog", lambda req: get_catalog(ctx, req))
    router.add("GET", "/api/v1/catalog-summaries", lambda req: get_catalog_summaries(ctx, req))
    router.add("GET", "/api/v1/catalog/{slug}", lambda req: get_catalog_entry(ctx, req))
    router.add("GET", "/api/v1/profile", lambda req: get_profile(ctx, req))
    router.add("GET", "/api/v1/preview", lambda req: get_preview(ctx, req))
    router.add("POST", "/api/v1/profile/enable", lambda req: post_profile_enable(ctx, req))
    router.add("POST", "/api/v1/profile/edit", lambda req: post_profile_edit(ctx, req))
    router.add("POST", "/api/v1/profile/remove", lambda req: post_profile_remove(ctx, req))
    router.add("POST", "/api/v1/profile/restore", lambda req: post_profile_restore(ctx, req))
    router.add("POST", "/api/v1/profile/local", lambda req: post_profile_local_add(ctx, req))
    router.add("DELETE", "/api/v1/profile/local/{slug}", lambda req: delete_profile_local(ctx, req))
    router.add("POST", "/api/v1/generate", lambda req: post_generate(ctx, req))
    router.add("GET", "/api/v1/generate/hpe/{slug}", lambda req: get_generate_hpe_list(ctx, req))
    router.add("GET", "/api/v1/history", lambda req: get_history(ctx, req))
    router.add("GET", "/api/v1/history/{id}", lambda req: get_history_entry(ctx, req))
    router.add("POST", "/api/v1/history/{id}/rollback", lambda req: post_history_rollback(ctx, req))
    router.add("GET", "/api/v1/export/{format}", lambda req: get_export(ctx, req))
    router.add("GET", "/api/v1/sources", lambda req: get_sources(ctx, req))
    router.add("GET", "/api/v1/sources/status", lambda req: get_sources_status(ctx, req))
    router.add("POST", "/api/v1/sources/configure", lambda req: post_sources_configure(ctx, req))
    router.add("POST", "/api/v1/sources/fetch", lambda req: post_sources_fetch(ctx, req))
    router.add("POST", "/api/v1/sources/update", lambda req: post_sources_update(ctx, req))
    router.add("GET", "/api/v1/sources/provenance/{slug}", lambda req: get_sources_provenance(ctx, req))
    router.add("POST", "/api/v1/hpe/inspect", lambda req: post_hpe_inspect(ctx, req))
    router.add("POST", "/api/v1/hpe/validate", lambda req: post_hpe_validate(ctx, req))
    router.add("POST", "/api/v1/hpe/build", lambda req: post_hpe_build(ctx, req))
    router.add("POST", "/api/v1/hpdb/inspect", lambda req: post_hpdb_inspect(ctx, req))
    router.add("POST", "/api/v1/hpdb/extract", lambda req: post_hpdb_extract(ctx, req))
    router.add("GET", "/api/v1/install/hpdb-inspect", lambda req: get_install_hpdb_inspect(ctx, req))
    router.add("POST", "/api/v1/merge/preview", lambda req: post_merge_preview(ctx, req))
    router.add("POST", "/api/v1/merge/apply", lambda req: post_merge_apply(ctx, req))
    router.add("GET", "/api/v1/install/detect", lambda req: get_install_detect(ctx, req))
    router.add("POST", "/api/v1/install/backup", lambda req: post_install_backup(ctx, req))
    router.add("POST", "/api/v1/install/write", lambda req: post_install_write(ctx, req))
    router.add("POST", "/api/v1/install/rollback", lambda req: post_install_rollback(ctx, req))
    return router
