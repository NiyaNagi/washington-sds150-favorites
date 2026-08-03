"""Command-line interface for wasds150.

Subcommands: init, catalog {show,validate,regenerate-baseline}, profile
{list,show,add,remove,edit,enable,disable,restore}, preview, generate,
history {list,show,rollback}, doctor, ui, hpe {encode,decode,inspect,
validate,build,hpdb-inspect,hpdb-extract}, merge {preview,apply}, sources
{list,status,configure,fetch,update,provenance}, install
{detect,backup,write,rollback,hpdb-inspect} (experimental).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from wasds150 import __version__
from wasds150.appctx import AppContext, build_context
from wasds150.bundle.generate_outputs import generate_outputs
from wasds150.catalog import baseline as catalog_baseline
from wasds150.catalog import loader as catalog_loader
from wasds150.catalog.ids import slugify, stable_id
from wasds150.catalog.validate import validate_catalog, validate_profile
from wasds150.config import AppConfig
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
from wasds150.installer.confirm import confirm_phrase_for
from wasds150.installer.rollback import rollback_from_backup
from wasds150.installer.writer import write_favorites_list
from wasds150.logging_setup import configure_logging
from wasds150.merge.three_way import apply_merge, three_way_merge
from wasds150.models.catalog import ORIGIN_LOCAL, Catalog, FavoritesList, System
from wasds150.models.profile import EDITABLE_FIELDS


def _build_config(args: argparse.Namespace) -> AppConfig:
    if args.home:
        return AppConfig(home=Path(args.home))
    return AppConfig.default()


def _build_ctx(args: argparse.Namespace) -> AppContext:
    config = _build_config(args)
    configure_logging(config.log_file)
    csv_override = Path(args.csv) if getattr(args, "csv", None) else None
    return build_context(config, csv_override=csv_override)


def _print_json(data) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


# ---------------------------------------------------------------- init ----
def cmd_init(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    ctx.config.ensure_dirs()
    if ctx.config.profile_path.exists() and not args.force:
        print(f"Profile already exists at {ctx.config.profile_path}; use --force to reset it.")
        return 0
    profile = ctx.load_profile()
    if not ctx.config.profile_path.exists():
        profile.based_on_catalog_hash = ctx.catalog.content_hash()
    if args.force:
        profile.entries.clear()
        profile.local_lists.clear()
        profile.based_on_catalog_hash = ctx.catalog.content_hash()
    ctx.save_profile(profile)
    print(f"Initialized wasds150 home at {ctx.config.home}")
    print(f"Catalog source: {ctx.catalog_source} ({len(ctx.catalog.favorites)} Favorites Lists)")
    print(f"Profile: {ctx.config.profile_path}")
    return 0


# ------------------------------------------------------------- catalog ----
def cmd_catalog_show(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    favorites = ctx.catalog.favorites
    if args.slug:
        favorites = [fl for fl in favorites if fl.slug == args.slug.lower()]
        if not favorites:
            print(f"No such favorite_key/slug: {args.slug}", file=sys.stderr)
            return 1
    if args.region:
        favorites = [fl for fl in favorites if args.region.lower() in fl.region.lower()]

    if args.json:
        _print_json([fl.to_dict() for fl in favorites])
        return 0

    for fl in favorites:
        print(f"{fl.favorite_key:8} {fl.slug:40} {fl.region:20} {fl.favorite_name}")
    print(f"\n{len(favorites)} Favorites Lists (source: {ctx.catalog_source})")
    return 0


def cmd_catalog_validate(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    issues = validate_catalog(ctx.catalog)
    if args.json:
        _print_json({"issues": issues})
    else:
        if not issues:
            print(f"OK: {len(ctx.catalog.favorites)} Favorites Lists, no issues found.")
        else:
            print(f"Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
    return 1 if issues else 0


def cmd_catalog_regenerate_baseline(args: argparse.Namespace) -> int:
    """Maintainer-only: regenerate the packaged ``data/baseline_catalog.json``
    from the repo CSV (see :mod:`wasds150.catalog.baseline`). Never called
    automatically."""
    csv_path = Path(args.csv) if args.csv else Path("washington-sds150-favorites.csv")
    out_path = Path(args.out) if args.out else catalog_baseline.baseline_resource_path()
    catalog = catalog_baseline.generate_baseline_from_csv(csv_path, out_path)
    with_systems = sum(1 for fl in catalog.favorites if fl.systems)
    if args.json:
        _print_json(
            {
                "out": str(out_path),
                "favorites": len(catalog.favorites),
                "with_systems": with_systems,
                "content_hash": catalog.content_hash(),
            }
        )
        return 0
    print(f"Wrote {out_path} ({len(catalog.favorites)} Favorites Lists, {with_systems} with populated systems)")
    print(f"Content hash: {catalog.content_hash()}")
    return 0


# ------------------------------------------------------------- profile ----
def cmd_profile_list(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)
    favorites = result.favorites if args.all else result.enabled_favorites

    if args.json:
        _print_json(
            {
                "favorites": [fl.to_dict() for fl in favorites],
                "counts": result.counts,
                "content_hash": result.content_hash,
            }
        )
        return 0

    for fl in favorites:
        state = "ENABLED" if fl.enabled else "disabled"
        override_marker = "*" if fl.slug in profile.entries else " "
        origin = "local" if fl.origin == ORIGIN_LOCAL else "base "
        print(f"{override_marker}{fl.favorite_key:8} {origin} {state:8} {fl.region:20} {fl.favorite_name}")
    print(f"\n{len(favorites)} shown; counts={result.counts}")
    return 0


def cmd_profile_show(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)
    slug = args.slug.lower()
    match = next((fl for fl in result.favorites if fl.slug == slug), None)
    if match is None:
        print(f"No such favorite in effective catalog: {slug}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(match.to_dict())
        return 0
    for f in match.__dataclass_fields__:
        if f in ("systems", "provenance"):
            continue
        print(f"{f}: {getattr(match, f)}")
    return 0


def _resolve_slug(ctx: AppContext, profile, raw_slug: str) -> Optional[str]:
    slug = raw_slug.strip().lower()
    if ctx.catalog.by_slug(slug) is not None or slug in profile.local_lists:
        return slug
    return None


def cmd_profile_enable(args: argparse.Namespace, enabled: bool) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    slug = _resolve_slug(ctx, profile, args.slug)
    if slug is None:
        print(f"Unknown slug: {args.slug}", file=sys.stderr)
        return 1
    if slug in profile.local_lists:
        profile.local_lists[slug].enabled = enabled
    else:
        profile.set_enabled(slug, enabled)
    ctx.save_profile(profile)
    print(f"{'Enabled' if enabled else 'Disabled'} {slug}")
    return 0


def cmd_profile_edit(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    slug = _resolve_slug(ctx, profile, args.slug)
    if slug is None:
        print(f"Unknown slug: {args.slug}", file=sys.stderr)
        return 1
    if args.field not in EDITABLE_FIELDS:
        print(f"Field {args.field!r} is not editable. Choices: {EDITABLE_FIELDS}", file=sys.stderr)
        return 1
    value = args.value
    if args.field == "flqk":
        value = int(value)

    if slug in profile.local_lists:
        setattr(profile.local_lists[slug], args.field, value)
    else:
        profile.set_override(slug, args.field, value)
    ctx.save_profile(profile)
    print(f"Set {slug}.{args.field} = {value!r}")
    return 0


def cmd_profile_remove(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    slug = _resolve_slug(ctx, profile, args.slug)
    if slug is None:
        print(f"Unknown slug: {args.slug}", file=sys.stderr)
        return 1
    if slug in profile.local_lists:
        profile.remove_local_list(slug)
    else:
        profile.set_removed(slug, True)
        if args.reason:
            profile.entry_for(slug).note = args.reason
    ctx.save_profile(profile)
    print(f"Removed {slug}")
    return 0


def cmd_profile_restore(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    slug = args.slug.strip().lower()
    if slug in profile.local_lists:
        print(f"{slug} is a local list; use 'profile remove' to delete it instead.", file=sys.stderr)
        return 1
    profile.restore(slug)
    ctx.save_profile(profile)
    print(f"Restored {slug} to baseline defaults")
    return 0


def cmd_profile_add(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    slug = slugify(args.key)
    if ctx.catalog.by_slug(slug) is not None:
        print(f"favorite_key/slug {slug!r} collides with a baseline entry.", file=sys.stderr)
        return 1
    if slug in profile.local_lists:
        print(f"A local list with key {slug!r} already exists.", file=sys.stderr)
        return 1

    fl = FavoritesList(
        id=stable_id(slug),
        slug=slug,
        favorite_key=args.key,
        favorite_name=args.name,
        region=args.region,
        counties=args.counties,
        scenario=args.scenario,
        source_type=args.source_type,
        system_or_category=args.system,
        sites_or_coverage=args.sites,
        departments_or_channels=args.departments,
        mode=args.mode,
        monitorability=args.monitorability,
        upgrade_required=args.upgrade,
        source_url=args.source_url,
        notes=args.notes,
        enabled=not args.disabled,
        flqk=args.flqk,
        origin=ORIGIN_LOCAL,
    )
    profile.add_local_list(fl)
    ctx.save_profile(profile)
    print(f"Added local Favorites List {slug}")
    return 0


# ------------------------------------------------------------- preview ----
def cmd_preview(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)
    changes = diff_profile(ctx.catalog, profile)

    if args.json:
        _print_json(
            {
                "counts": result.counts,
                "content_hash": result.content_hash,
                "warnings": result.warnings,
                "changes": [c.to_dict() for c in changes],
            }
        )
        return 0

    print(f"Preview (no files written, no snapshot committed)")
    print(f"Catalog source: {ctx.catalog_source}")
    print(f"Counts: {result.counts}")
    print(f"Content hash: {result.content_hash}")
    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  - {w}")
    if changes:
        print(f"\nChanges vs. raw baseline ({len(changes)}):")
        for c in changes:
            if c.op == "edit":
                print(f"  edit    {c.slug}.{c.field}: {c.before!r} -> {c.after!r}")
            else:
                print(f"  {c.op:7} {c.slug} ({c.label})")
    else:
        print("\nNo changes vs. raw baseline.")
    return 0


# ------------------------------------------------------------- generate ----
def cmd_generate(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    try:
        published = generate_outputs(result, out_dir, formats)
    except (HpeValidationError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    written = published.files

    ctx.config.ensure_dirs()
    store = SnapshotStore(ctx.config.history_dir)
    snap = store.commit(profile, result, message=args.message or "")

    all_warnings = list(result.warnings) + published.warnings
    if args.json:
        _print_json(
            {
                "snapshot_id": snap.id,
                "content_hash": result.content_hash,
                "counts": result.counts,
                "warnings": all_warnings,
                "files": [str(p) for p in written],
            }
        )
        return 0

    print(f"Generated {len(result.enabled_favorites)} enabled Favorites Lists")
    print(f"Snapshot committed: {snap.id} ({snap.created_at})")
    print(f"Content hash: {result.content_hash}")
    for p in written:
        print(f"  wrote {p}")
    if all_warnings:
        print(f"Warnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(f"  - {w}")
    return 0


# -------------------------------------------------------------- history ----
def cmd_history_list(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    store = SnapshotStore(ctx.config.history_dir)
    snapshots = store.list()
    if args.json:
        _print_json([s.__dict__ for s in snapshots])
        return 0
    for s in snapshots:
        print(f"{s.id}  {s.created_at}  {s.content_hash[:12]}  {s.message}")
    print(f"\n{len(snapshots)} snapshot(s)")
    return 0


def cmd_history_show(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    store = SnapshotStore(ctx.config.history_dir)
    try:
        data = store.load_raw(args.id)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    _print_json(data)
    return 0


def cmd_history_rollback(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    store = SnapshotStore(ctx.config.history_dir)
    try:
        store.load_raw(args.id)
    except KeyError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not args.yes:
        print(f"This will overwrite {ctx.config.profile_path} with snapshot {args.id}.")
        print("Re-run with --yes to confirm (a timestamped backup of the current profile is kept).")
        return 1
    path = rollback_profile(ctx.config.profile_path, ctx.config.history_dir, args.id)
    print(f"Rolled back profile to snapshot {args.id}: {path}")
    return 0


# --------------------------------------------------------------- doctor ----
def cmd_doctor(args: argparse.Namespace) -> int:
    checks = []

    checks.append(("python_version", sys.version_info >= (3, 9), sys.version))

    try:
        ctx = _build_ctx(args)
        checks.append(("catalog_loads", True, f"{len(ctx.catalog.favorites)} favorites from {ctx.catalog_source}"))
        issues = validate_catalog(ctx.catalog)
        checks.append(("catalog_valid", not issues, f"{len(issues)} issue(s)"))
    except Exception as exc:  # pragma: no cover - defensive
        ctx = None
        checks.append(("catalog_loads", False, str(exc)))
        checks.append(("catalog_valid", False, "skipped"))

    if ctx is not None:
        try:
            ctx.config.ensure_dirs()
            checks.append(("home_writable", True, str(ctx.config.home)))
        except Exception as exc:  # pragma: no cover - defensive
            checks.append(("home_writable", False, str(exc)))

        profile_ok = True
        profile_detail = "no profile yet"
        if ctx.config.profile_path.exists():
            try:
                profile = ctx.load_profile()
                profile_issues = validate_profile(profile, ctx.catalog)
                profile_ok = not profile_issues
                profile_detail = f"{len(profile_issues)} issue(s)"
            except Exception as exc:  # pragma: no cover - defensive
                profile_ok = False
                profile_detail = str(exc)
        checks.append(("profile_valid", profile_ok, profile_detail))

    static_dir = Path(__file__).parent / "webui" / "static" / "index.html"
    checks.append(("webui_assets", static_dir.exists(), str(static_dir)))

    ok = all(passed for _, passed, _ in checks)
    if args.json:
        _print_json({"ok": ok, "checks": [{"name": n, "ok": p, "detail": d} for n, p, d in checks]})
    else:
        for name, passed, detail in checks:
            print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        print(f"\nOverall: {'OK' if ok else 'PROBLEMS FOUND'}")
    return 0 if ok else 1


# ------------------------------------------------------------------- ui ----
def cmd_ui(args: argparse.Namespace) -> int:
    from wasds150.webui.server import run_server

    ctx = _build_ctx(args)
    ctx.config.ensure_dirs()
    return run_server(ctx, port=args.port, open_browser=not args.no_browser)


# ------------------------------------------------------------------- hpe ----
def cmd_hpe_decode(args: argparse.Namespace) -> int:
    data = Path(args.file).read_bytes()
    try:
        text = hpe_codec.decode_container(data, max_decompressed_size=args.max_size)
    except hpe_codec.HpeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.out:
        Path(args.out).write_bytes(text.encode("ascii"))
        print(f"wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def cmd_hpe_encode(args: argparse.Namespace) -> int:
    text = Path(args.file).read_bytes().decode("ascii")
    try:
        document = parse_records(text)
        require_valid_document(document, context=str(args.file))
        data = hpe_codec.encode_container(text)
        require_valid_hpe_container(data, context=str(args.out))
    except (hpe_codec.HpeError, HpeValidationError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    out_path = Path(args.out)
    out_path.write_bytes(data)
    print(f"wrote {out_path} ({len(data)} bytes)")
    return 0


def _load_hpe_text(path: Path, max_size: int) -> str:
    data = path.read_bytes()
    # A .hpe container starts as XOR(gzip(...)); gzip's magic bytes 0x1f8b
    # XORed with 0x0C are 0x13,0x87 — cheaper and more robust than trying
    # gzip and falling back, and avoids ever mis-detecting plain .hpd text
    # (which is required to be printable ASCII) as a container.
    if len(data) >= 2 and data[0] == (0x1F ^ hpe_codec.XOR_KEY) and data[1] == (0x8B ^ hpe_codec.XOR_KEY):
        return hpe_codec.decode_container(data, max_decompressed_size=max_size)
    return data.decode("ascii")


def cmd_hpe_inspect(args: argparse.Namespace) -> int:
    text = _load_hpe_text(Path(args.file), args.max_size)
    doc = parse_records(text)
    dialect = hpe_schema.detect_dialect(doc)
    tag_counts: dict = {}
    for r in doc.records:
        tag_counts[r.tag] = tag_counts.get(r.tag, 0) + 1

    if args.json:
        _print_json(
            {
                "dialect": {"target_model": dialect.target_model, "format_version": dialect.format_version}
                if dialect
                else None,
                "has_signature_line": hpe_codec.has_signature_line(text),
                "record_count": len(doc.records),
                "tag_counts": tag_counts,
            }
        )
        return 0

    print(f"Dialect: {dialect.target_model}/{dialect.format_version}" if dialect else "Dialect: unknown")
    print(f"Signature line present: {hpe_codec.has_signature_line(text)}")
    print(f"Total records: {len(doc.records)}")
    print()
    nodes = hpe_tree.build_tree(doc)
    print(hpe_tree.render_tree(nodes))
    return 0


def cmd_hpe_validate(args: argparse.Namespace) -> int:
    text = _load_hpe_text(Path(args.file), args.max_size)
    doc = parse_records(text)
    dialect = hpe_schema.detect_dialect(doc)
    semantic_issues = validate_document(doc) if dialect and dialect.is_bcdx36hp else []
    issues = [str(issue) for issue in semantic_issues] or hpe_schema.validate_schema(doc, dialect)

    if args.json:
        _print_json({"issues": issues, "dialect": dialect.target_model if dialect else None})
        return 0
    if not issues:
        print(f"OK: {len(doc.records)} records, dialect "
              f"{dialect.target_model}/{dialect.format_version if dialect else '?'}, no issues")
        return 0
    print(f"Found {len(issues)} issue(s):")
    for issue in issues:
        print(f"  - {issue}")
    return 1


def cmd_hpe_build(args: argparse.Namespace) -> int:
    data = json.loads(Path(args.systems).read_text(encoding="utf-8"))
    raw_systems = data["systems"] if isinstance(data, dict) else data
    systems = [System.from_dict(s) for s in raw_systems]
    doc = hpe_builders.build_favorites_document(systems)
    model_issues = validate_systems(systems)
    if model_issues:
        print(f"Validation failed ({len(model_issues)} issue(s)):", file=sys.stderr)
        for issue in model_issues:
            print(f"  - {issue}", file=sys.stderr)
        return 1
    try:
        require_valid_document(doc)
    except HpeValidationError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    text = serialize_records(doc)
    out_path = Path(args.out)
    if out_path.suffix == ".hpe":
        data = hpe_codec.encode_container(text)
        try:
            require_valid_hpe_container(data)
        except HpeValidationError as exc:
            print(f"Validation failed: {exc}", file=sys.stderr)
            return 1
        out_path.write_bytes(data)
    else:
        out_path.write_bytes(text.encode("ascii"))
    print(f"wrote {out_path} ({len(systems)} system(s), {len(doc.records)} records)")
    return 0


def _load_hpdb_doc(path: Path):
    """Auto-detect and parse an ``hpdb.cfg`` (state/county index) vs a
    ``s_<state>.hpd`` (full system list) file."""
    text = path.read_bytes().decode("ascii")
    doc = parse_records(text)
    is_index = doc.find_first("StateInfo") is not None or doc.find_first("CountyInfo") is not None
    return doc, ("hpdb_index" if is_index else "hpdb_state")


def cmd_hpe_hpdb_inspect(args: argparse.Namespace) -> int:
    doc, kind = _load_hpdb_doc(Path(args.file))

    if kind == "hpdb_index":
        index = hpe_hpdb.CountyIndex.from_hpdb_cfg(doc)
        if args.json:
            _print_json(
                {
                    "kind": kind,
                    "states": index.state_by_id,
                    "counties": [{"id": cid, "name": name, "state_id": index.county_state.get(cid)} for cid, name in index.by_id.items()],
                }
            )
            return 0
        print(f"hpdb.cfg: {len(index.state_by_id)} state(s), {len(index.by_id)} count(y/ies)")
        for state_id, name in index.state_by_id.items():
            print(f"  StateId={state_id}: {name}")
        for cid, name in index.by_id.items():
            print(f"    CountyId={cid}: {name} (state {index.county_state.get(cid)})")
        return 0

    systems = hpe_hpdb.segment_systems(doc)
    if args.json:
        _print_json(
            [
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
            ]
        )
        return 0
    print(f"s_<state>.hpd: {len(systems)} system(s)")
    for s in systems:
        print(f"  {s.kind():12} {s.name():30} id={s.identity()} counties={s.county_ids()} states={s.state_ids()}")
    return 0


def cmd_hpe_hpdb_extract(args: argparse.Namespace) -> int:
    doc, kind = _load_hpdb_doc(Path(args.file))
    if kind != "hpdb_state":
        print("error: --county-id/--within extraction requires a s_<state>.hpd system file, not hpdb.cfg", file=sys.stderr)
        return 1

    systems = hpe_hpdb.segment_systems(doc)
    if args.county_id is not None:
        systems = hpe_hpdb.by_county(systems, args.county_id)
    if args.within:
        try:
            lat_s, lon_s, radius_s = args.within.split(",")
            systems = hpe_hpdb.within_radius(systems, float(lat_s), float(lon_s), float(radius_s))
        except ValueError:
            print("error: --within must be 'LAT,LON,RADIUS_MILES'", file=sys.stderr)
            return 1

    if not systems:
        print("No systems matched the given filter(s).", file=sys.stderr)
        return 1

    records = list(he_hpdb_preamble(doc))
    for s in systems:
        records.extend(s.records)
    from wasds150.hpe.record import new_document

    subset_doc = new_document(records, line_ending="\r\n")
    fav_doc = hpe_hpdb.to_favorites_dialect(subset_doc, synthesize_dqks=not args.no_dqks)
    if fav_doc.find_first("File") is None:
        from wasds150.hpe.record import Record

        fav_doc.records.append(Record(tag="File", fields=["HomePatrol Export File"]))
        fav_doc.line_endings.append("\r\n")

    text = serialize_records(fav_doc)
    try:
        require_valid_document(fav_doc, context="HPDB extraction")
    except HpeValidationError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1
    out_path = Path(args.out)
    if out_path.suffix == ".hpe":
        data = hpe_codec.encode_container(text)
        try:
            require_valid_hpe_container(data, context="HPDB extraction")
        except HpeValidationError as exc:
            print(f"Validation failed: {exc}", file=sys.stderr)
            return 1
        out_path.write_bytes(data)
    else:
        out_path.write_bytes(text.encode("ascii"))
    print(f"wrote {out_path} ({len(systems)} system(s) extracted)")
    return 0


def he_hpdb_preamble(doc):
    """``TargetModel``/``FormatVersion`` header only (not the full
    ``preamble_records``, which for a ``s_<state>.hpd`` file could also
    include StateInfo/CountyInfo not meaningful outside their own document)."""
    return [r for r in hpe_hpdb.preamble_records(doc) if r.tag in ("TargetModel", "FormatVersion")]


# ----------------------------------------------------------------- merge ----
def _load_upstream_catalog(path: Path) -> Catalog:
    if path.suffix.lower() == ".json":
        return catalog_loader.load_json(path)
    return catalog_loader.load_csv(path)


def cmd_merge_preview(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    upstream = _load_upstream_catalog(Path(args.upstream))
    result = three_way_merge(ctx.catalog, upstream, profile)

    if args.json:
        _print_json(result.to_dict())
        return 0

    print(f"Base catalog: {ctx.catalog_source} ({len(ctx.catalog.favorites)} lists)")
    print(f"Upstream: {args.upstream} ({len(upstream.favorites)} lists)")
    print(f"\nChanges ({len(result.changes)}):")
    for c in result.changes:
        if c.field:
            print(f"  {c.op:8} {c.slug}.{c.field}: {c.before!r} -> {c.after!r}")
        else:
            print(f"  {c.op:8} {c.slug} ({c.label})")
    if result.conflicts:
        print(f"\nCONFLICTS ({len(result.conflicts)}) — local overrides disagree with upstream:")
        for c in result.conflicts:
            print(f"  {c.slug}.{c.field}: base={c.base_value!r} upstream={c.upstream_value!r} local={c.local_value!r}")
    else:
        print("\nNo conflicts.")
    return 1 if result.conflicts else 0


def cmd_merge_apply(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    upstream = _load_upstream_catalog(Path(args.upstream))
    result = three_way_merge(ctx.catalog, upstream, profile)

    if result.conflicts and not args.force:
        print(f"{len(result.conflicts)} conflict(s) found; re-run with --force to apply anyway "
              "(local overrides are preserved either way — see 'wasds150 merge preview').", file=sys.stderr)
        return 1

    new_profile = apply_merge(profile, result)
    ctx.save_catalog(result.merged_catalog)
    ctx.save_profile(new_profile)

    if args.json:
        _print_json(
            {
                "merged_catalog_hash": result.merged_catalog.content_hash(),
                "changes": len(result.changes),
                "conflicts": len(result.conflicts),
            }
        )
        return 0
    print(f"Merged catalog saved to {ctx.config.catalog_path}")
    print(f"Applied {len(result.changes)} change(s); {len(result.conflicts)} conflict(s) (overrides preserved).")
    return 0


# -------------------------------------------------------------- sources ----
def _build_http_client(config: AppConfig, offline: bool):
    from wasds150.cache.http import CachedHttpClient
    from wasds150.cache.store import HttpCacheStore

    return CachedHttpClient(HttpCacheStore(config.cache_dir), offline=offline)


def _instantiate_source(name: str, sources_config) -> Optional[Any]:
    """Build a ready-to-run adapter instance for ``sources fetch``/``update``,
    or ``None`` if ``name`` is a legacy/local adapter with nothing
    configured to run against (e.g. ``sentinel_local`` with no path set)."""
    from wasds150.sources.base import OnlineSourceAdapter
    from wasds150.sources.radioreference_premium import RadioReferenceCredentials, RadioReferencePremiumSource
    from wasds150.sources.registry import get_source_class
    from wasds150.sources.sentinel_local import SentinelLocalSource

    cls = get_source_class(name)
    if not issubclass(cls, OnlineSourceAdapter):
        return None  # static_pack / legacy placeholders: not part of the update pipeline

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


def cmd_sources_list(args: argparse.Namespace) -> int:
    from wasds150.sources.base import OnlineSourceAdapter
    from wasds150.sources.registry import list_sources

    rows = []
    for name, cls in sorted(list_sources().items()):
        kind = getattr(cls, "kind", None) if issubclass(cls, OnlineSourceAdapter) else "legacy"
        rows.append({"name": name, "available": cls.available, "kind": kind})

    if args.json:
        _print_json({"sources": rows})
        return 0
    for row in rows:
        print(f"  {row['name']:24} available={row['available']!s:5} kind={row['kind']}")
    return 0


def cmd_sources_status(args: argparse.Namespace) -> int:
    from wasds150.cache.store import HttpCacheStore
    from wasds150.sources.config import SourcesConfig
    from wasds150.sources.registry import list_sources

    config = _build_config(args)
    sources_config = SourcesConfig.load(config.sources_config_path)
    store = HttpCacheStore(config.cache_dir)

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
    if args.json:
        _print_json({"offline": sources_config.offline, "sources": rows})
        return 0
    print(f"Offline mode: {sources_config.offline}")
    for row in rows:
        print(f"  {row['name']:24} cached_urls={row['cached_urls']:3} last_fetch={row['most_recent_fetch']}")
    return 0


def cmd_sources_configure(args: argparse.Namespace) -> int:
    from wasds150.sources.config import SourcesConfig

    config = _build_config(args)
    config.ensure_dirs()
    sources_config = SourcesConfig.load(config.sources_config_path)

    if args.online:
        sources_config.offline = False
    if args.offline:
        sources_config.offline = True
    if args.sentinel_mount is not None:
        sources_config.sentinel_local_mount = args.sentinel_mount or None
        sources_config.sentinel_local_hpdb_cfg = None
    if args.sentinel_hpdb_cfg is not None:
        sources_config.sentinel_local_hpdb_cfg = args.sentinel_hpdb_cfg or None
        sources_config.sentinel_local_mount = None
    if args.rr_export_path is not None:
        sources_config.radioreference_export_path = args.rr_export_path or None
    if args.rr_username is not None:
        sources_config.radioreference_username = args.rr_username or None
    if args.rr_app_key is not None:
        sources_config.radioreference_app_key = args.rr_app_key or None

    sources_config.save(config.sources_config_path)
    # Never echo credential-like values back, even redacted -- only confirm
    # which non-secret fields are now set.
    if args.json:
        _print_json(
            {
                "offline": sources_config.offline,
                "sentinel_local_configured": bool(
                    sources_config.sentinel_local_mount or sources_config.sentinel_local_hpdb_cfg
                ),
                "radioreference_configured": bool(
                    sources_config.radioreference_export_path
                    or (sources_config.radioreference_username and sources_config.radioreference_app_key)
                ),
            }
        )
        return 0
    print(f"Saved source configuration to {config.sources_config_path}")
    print(f"  offline={sources_config.offline}")
    print(f"  sentinel_local configured={bool(sources_config.sentinel_local_mount or sources_config.sentinel_local_hpdb_cfg)}")
    print(
        "  radioreference_premium configured="
        f"{bool(sources_config.radioreference_export_path or (sources_config.radioreference_username and sources_config.radioreference_app_key))}"
    )
    return 0


def cmd_sources_fetch(args: argparse.Namespace) -> int:
    from wasds150.sources.config import SourcesConfig
    from wasds150.update.pipeline import run_sources

    config = _build_config(args)
    configure_logging(config.log_file)
    sources_config = SourcesConfig.load(config.sources_config_path)
    source = _instantiate_source(args.name, sources_config)
    if source is None:
        print(f"Source {args.name!r} is not configured/runnable (see 'wasds150 sources configure').", file=sys.stderr)
        return 1

    http_client = _build_http_client(config, sources_config.offline) if source.kind != "local" else None
    run = run_sources([source], http_client=http_client)
    outcome = run.outcomes[0]
    if args.json:
        _print_json({"outcome": outcome.to_dict(), "facts": [f.to_dict() for f in run.facts]})
        return 0 if outcome.ok else 1
    print(f"{outcome.source_id}: ok={outcome.ok} facts={outcome.fact_count} alerts={outcome.alert_count}")
    for w in outcome.warnings:
        print(f"  warning: {w}")
    if outcome.error:
        print(f"  error: {outcome.error}", file=sys.stderr)
    return 0 if outcome.ok else 1


def cmd_sources_update(args: argparse.Namespace) -> int:
    from wasds150.sources.base import OnlineSourceAdapter
    from wasds150.sources.config import SourcesConfig
    from wasds150.sources.registry import list_sources
    from wasds150.update.pipeline import build_and_merge, run_sources

    ctx = _build_ctx(args)
    sources_config = SourcesConfig.load(ctx.config.sources_config_path)
    offline = sources_config.offline or args.offline

    only = set(args.only.split(",")) if args.only else None
    instances = []
    for name, cls in list_sources().items():
        if not issubclass(cls, OnlineSourceAdapter) or not cls.available:
            continue
        if only is not None and name not in only:
            continue
        instance = _instantiate_source(name, sources_config)
        if instance is not None:
            instances.append(instance)

    http_client = _build_http_client(ctx.config, offline)
    run = run_sources(instances, http_client=http_client)
    profile = ctx.load_profile()
    built = build_and_merge(ctx.catalog, profile, run.facts)
    merge_result = built["merge"]
    coverage = built["coverage"]

    if args.apply:
        if merge_result.conflicts and not args.force:
            print(
                f"{len(merge_result.conflicts)} conflict(s) found; re-run with --force to apply anyway.",
                file=sys.stderr,
            )
            return 1
        new_profile = apply_merge(profile, merge_result)
        ctx.save_catalog(merge_result.merged_catalog)
        ctx.save_profile(new_profile)

    if args.json:
        _print_json(
            {
                "run": run.to_dict(),
                "coverage": [c.to_dict() for c in coverage],
                "merge": merge_result.to_dict(),
                "applied": bool(args.apply),
            }
        )
        return 0

    print(f"Ran {len(instances)} source(s):")
    for outcome in run.outcomes:
        status = "ok" if outcome.ok else f"FAILED: {outcome.error}"
        print(f"  {outcome.source_id}: {status} ({outcome.fact_count} facts, {outcome.alert_count} alerts)")
    partial_or_none = [c for c in coverage if c.status != "full"]
    print(f"\nCoverage: {len(coverage) - len(partial_or_none)}/{len(coverage)} rows full")
    for c in partial_or_none:
        for w in c.warnings:
            print(f"  {c.favorite_key}: {w}")
    print(f"\nMerge: {len(merge_result.changes)} change(s), {len(merge_result.conflicts)} conflict(s)")
    if args.apply:
        print("Applied." if not merge_result.conflicts or args.force else "NOT applied (conflicts).")
    else:
        print("(preview only; re-run with --apply to persist)")
    return 1 if merge_result.conflicts and args.apply and not args.force else 0


def cmd_sources_provenance(args: argparse.Namespace) -> int:
    ctx = _build_ctx(args)
    fl = ctx.catalog.by_slug(args.slug.lower())
    if fl is None:
        print(f"No such favorite: {args.slug}", file=sys.stderr)
        return 1
    if args.json:
        _print_json({"slug": fl.slug, "provenance": [p.to_dict() for p in fl.provenance]})
        return 0
    print(f"{fl.favorite_key} — {fl.favorite_name}")
    for p in fl.provenance:
        print(f"  {p.source_adapter:24} confidence={p.confidence:10} url={p.source_url} fetched_at={p.fetched_at}")
    return 0


# --------------------------------------------------------------- install ----
def cmd_install_detect(args: argparse.Namespace) -> int:
    candidate_dirs = [Path(d) for d in args.dir] if args.dir else None
    volumes = installer_detect.detect_volumes(candidate_dirs)
    if args.json:
        _print_json(
            [
                {"mount_point": str(v.mount_point), "label": v.label, "is_sds150_candidate": v.is_sds150_candidate}
                for v in volumes
            ]
        )
        return 0
    for v in volumes:
        marker = "SDS150" if v.is_sds150_candidate else "not SDS150"
        print(f"{v.mount_point}  ({marker})")
    if not volumes:
        print("No candidate volumes found. Pass --dir explicitly to check a specific mount point.")
    return 0


def cmd_install_backup(args: argparse.Namespace) -> int:
    try:
        path = backup_card(Path(args.mount), Path(args.out_dir))
    except InstallerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    issues = verify_backup(path)
    if args.json:
        _print_json({"backup_path": str(path), "verify_issues": issues})
        return 0
    print(f"Backup written: {path}")
    if issues:
        print(f"Backup verification issues: {issues}", file=sys.stderr)
        return 1
    print("Backup verified OK.")
    return 0


def _resolve_generated_favorites_list(args: argparse.Namespace, slug_or_key: str) -> FavoritesList:
    """Resolve one Favorites List from the current profile's *generated*
    output (baseline + profile overrides + Tier C static systems — see
    :mod:`wasds150.generate.pipeline`), by slug or ``favorite_key``. This
    is the default install workflow: profile -> generated favorites ->
    install, so a user never has to hand-author Systems JSON for a row
    this project can already populate on its own."""
    ctx = _build_ctx(args)
    profile = ctx.load_profile()
    result = apply_profile(ctx.catalog, profile)
    key = slug_or_key.strip()
    fl = next((f for f in result.favorites if f.slug == key.lower() or f.favorite_key == key), None)
    if fl is None:
        raise InstallerError(f"no such generated Favorites List: {slug_or_key!r} (see 'wasds150 profile list')")
    if not fl.systems:
        raise InstallerError(
            f"{fl.favorite_key} ({fl.favorite_name}) has no structured systems yet -- run "
            "'wasds150 sources configure' + 'wasds150 sources update --apply' to supply a local Sentinel "
            "HPDB export or RadioReference Premium data, or pass --systems for a hand-authored/debug entry."
        )
    return fl


def _resolve_install_systems(args: argparse.Namespace) -> "tuple[List[System], str]":
    """Resolve ``(systems, default_user_name)`` for ``install write``, from
    either ``--slug`` (default: profile -> generated favorites) or
    ``--systems`` (advanced/debug: raw JSON). Exactly one must be given."""
    if bool(args.slug) == bool(args.systems):
        raise InstallerError("pass exactly one of --slug (generated Favorites List) or --systems (raw JSON, advanced/debug)")
    if args.slug:
        fl = _resolve_generated_favorites_list(args, args.slug)
        return fl.systems, fl.favorite_name
    data = json.loads(Path(args.systems).read_text(encoding="utf-8"))
    raw_systems = data["systems"] if isinstance(data, dict) else data
    return [System.from_dict(s) for s in raw_systems], ""


def cmd_install_write(args: argparse.Namespace) -> int:
    try:
        systems, default_user_name = _resolve_install_systems(args)
    except InstallerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    user_name = args.user_name or default_user_name
    if not user_name:
        print("error: --user-name is required when using --systems (no generated Favorites List to default it from)", file=sys.stderr)
        return 1

    doc = hpe_builders.build_favorites_document(systems)

    dry_run = not args.execute
    try:
        result = write_favorites_list(
            Path(args.mount),
            index=args.index,
            document=doc,
            user_name=user_name,
            backup_dir=Path(args.backup_dir),
            confirm_phrase=args.confirm,
            dry_run=dry_run,
        )
    except InstallerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        _print_json(
            {
                "dry_run": result.dry_run,
                "planned_writes": result.planned_writes,
                "planned_deletes": result.planned_deletes,
                "backup_path": str(result.backup_path) if result.backup_path else None,
                "written_files": result.written_files,
                "deleted_files": result.deleted_files,
                "verified": result.verified,
                "warnings": result.warnings,
            }
        )
        return 0 if (result.dry_run or result.verified) else 1

    if result.dry_run:
        print(f"DRY RUN (pass --execute --confirm '{confirm_phrase_for(Path(args.mount))}' to write for real):")
        print(f"  would write: {result.planned_writes}")
        print(f"  would delete: {result.planned_deletes}")
        return 0

    print(f"Backup: {result.backup_path}")
    print(f"Wrote: {result.written_files}")
    print(f"Deleted: {result.deleted_files}")
    print(f"Verified: {result.verified}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")
    return 0 if result.verified else 1


def cmd_install_rollback(args: argparse.Namespace) -> int:
    try:
        restored = rollback_from_backup(Path(args.mount), Path(args.backup))
    except (InstallerError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.json:
        _print_json({"restored": restored})
        return 0
    print(f"Restored {len(restored)} file(s) from {args.backup}:")
    for r in restored:
        print(f"  {r}")
    return 0


def cmd_install_hpdb_inspect(args: argparse.Namespace) -> int:
    """Read-only: list the states/counties and systems found in a card's
    ``BCDx36HP/HPDB/`` tree. Never writes anything (HPDB is not on the
    installer's write allow-list; see wasds150.installer.paths)."""
    mount = Path(args.mount)
    if not installer_hpdb_reader.has_hpdb(mount):
        print(f"error: no HPDB/hpdb.cfg found under {mount}", file=sys.stderr)
        return 1
    card = installer_hpdb_reader.read_card_hpdb(mount)

    if args.json:
        payload = {
            "states": card.county_index.state_by_id if card.county_index else {},
            "counties": (
                [{"id": cid, "name": name} for cid, name in card.county_index.by_id.items()]
                if card.county_index
                else []
            ),
            "state_files": {
                str(state_id): [s.name() for s in hpe_hpdb.segment_systems(doc)]
                for state_id, doc in card.state_files.items()
            },
        }
        _print_json(payload)
        return 0

    if card.county_index:
        print(f"States: {card.county_index.state_by_id}")
        print(f"Counties: {card.county_index.by_id}")
    for state_id, doc in card.state_files.items():
        systems = hpe_hpdb.segment_systems(doc)
        print(f"\ns_{state_id:06d}.hpd: {len(systems)} system(s)")
        for s in systems:
            print(f"  {s.kind():12} {s.name()}")
    return 0


# --------------------------------------------------------------- parser ----
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="wasds150", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--home", help="Override the wasds150 home/config directory")
    parser.add_argument("--csv", help="Load the catalog from this CSV instead of the packaged baseline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init", help="Initialize the wasds150 home directory and profile")
    p_init.add_argument("--force", action="store_true", help="Reset an existing profile")
    p_init.set_defaults(func=cmd_init)

    p_catalog = subparsers.add_parser("catalog", help="Inspect the baseline catalog")
    catalog_sub = p_catalog.add_subparsers(dest="catalog_command", required=True)

    p_catalog_show = catalog_sub.add_parser("show", help="List/show baseline Favorites Lists")
    p_catalog_show.add_argument("--slug", help="Filter to one favorite_key/slug")
    p_catalog_show.add_argument("--region", help="Filter by substring match on region")
    p_catalog_show.add_argument("--json", action="store_true")
    p_catalog_show.set_defaults(func=cmd_catalog_show)

    p_catalog_validate = catalog_sub.add_parser("validate", help="Validate the baseline catalog")
    p_catalog_validate.add_argument("--json", action="store_true")
    p_catalog_validate.set_defaults(func=cmd_catalog_validate)

    p_catalog_regen = catalog_sub.add_parser(
        "regenerate-baseline",
        help="MAINTAINER-ONLY: regenerate the packaged data/baseline_catalog.json from the repo CSV",
    )
    p_catalog_regen.add_argument("--csv", help="Source CSV (default: ./washington-sds150-favorites.csv)")
    p_catalog_regen.add_argument("--out", help="Output path (default: the installed package's data/baseline_catalog.json)")
    p_catalog_regen.add_argument("--json", action="store_true")
    p_catalog_regen.set_defaults(func=cmd_catalog_regenerate_baseline)

    p_profile = subparsers.add_parser("profile", help="Manage the user profile (overrides on the baseline)")
    profile_sub = p_profile.add_subparsers(dest="profile_command", required=True)

    p_list = profile_sub.add_parser("list", help="List the effective (profile-applied) Favorites Lists")
    p_list.add_argument("--all", action="store_true", help="Include disabled lists")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_profile_list)

    p_show = profile_sub.add_parser("show", help="Show one effective Favorites List in detail")
    p_show.add_argument("slug")
    p_show.add_argument("--json", action="store_true")
    p_show.set_defaults(func=cmd_profile_show)

    p_enable = profile_sub.add_parser("enable", help="Enable a Favorites List")
    p_enable.add_argument("slug")
    p_enable.set_defaults(func=lambda a: cmd_profile_enable(a, True))

    p_disable = profile_sub.add_parser("disable", help="Disable a Favorites List")
    p_disable.add_argument("slug")
    p_disable.set_defaults(func=lambda a: cmd_profile_enable(a, False))

    p_edit = profile_sub.add_parser("edit", help="Override a single field on a Favorites List")
    p_edit.add_argument("slug")
    p_edit.add_argument("--field", required=True, choices=list(EDITABLE_FIELDS))
    p_edit.add_argument("--value", required=True)
    p_edit.set_defaults(func=cmd_profile_edit)

    p_remove = profile_sub.add_parser("remove", help="Remove a Favorites List (baseline: hide via profile; local: delete)")
    p_remove.add_argument("slug")
    p_remove.add_argument("--reason", help="Optional note explaining the removal")
    p_remove.set_defaults(func=cmd_profile_remove)

    p_restore = profile_sub.add_parser("restore", help="Discard all profile overrides for a baseline Favorites List")
    p_restore.add_argument("slug")
    p_restore.set_defaults(func=cmd_profile_restore)

    p_add = profile_sub.add_parser("add", help="Add a new local (user-authored) Favorites List")
    p_add.add_argument("--key", required=True, help="favorite_key, e.g. LOCAL01")
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--region", default="")
    p_add.add_argument("--counties", default="")
    p_add.add_argument("--scenario", default="")
    p_add.add_argument("--source-type", dest="source_type", default="")
    p_add.add_argument("--system", dest="system", default="")
    p_add.add_argument("--sites", default="")
    p_add.add_argument("--departments", default="")
    p_add.add_argument("--mode", default="")
    p_add.add_argument("--monitorability", default="")
    p_add.add_argument("--upgrade", dest="upgrade", default="")
    p_add.add_argument("--source-url", dest="source_url", default="")
    p_add.add_argument("--notes", default="")
    p_add.add_argument("--flqk", type=int, default=None)
    p_add.add_argument("--disabled", action="store_true")
    p_add.set_defaults(func=cmd_profile_add)

    p_preview = subparsers.add_parser("preview", help="Show what generate would do, without writing anything")
    p_preview.add_argument("--json", action="store_true")
    p_preview.set_defaults(func=cmd_preview)

    p_generate = subparsers.add_parser("generate", help="Generate output bundle(s) and commit a snapshot")
    p_generate.add_argument("--out", default="wasds150-output", help="Output directory")
    p_generate.add_argument(
        "--formats",
        default="csv,md,zip,hpe",
        help="Comma-separated: csv,md,zip,hpe ('zip' already embeds per-list .hpe files under hpe/; "
        "'hpe' additionally writes them loose into --out/hpe/)",
    )
    p_generate.add_argument("--message", default="", help="Snapshot message")
    p_generate.add_argument("--json", action="store_true")
    p_generate.set_defaults(func=cmd_generate)

    p_history = subparsers.add_parser("history", help="Snapshot history and rollback")
    history_sub = p_history.add_subparsers(dest="history_command", required=True)

    p_hist_list = history_sub.add_parser("list", help="List snapshots")
    p_hist_list.add_argument("--json", action="store_true")
    p_hist_list.set_defaults(func=cmd_history_list)

    p_hist_show = history_sub.add_parser("show", help="Show one snapshot")
    p_hist_show.add_argument("id")
    p_hist_show.set_defaults(func=cmd_history_show)

    p_hist_rollback = history_sub.add_parser("rollback", help="Restore the profile to a prior snapshot")
    p_hist_rollback.add_argument("id")
    p_hist_rollback.add_argument("--yes", action="store_true", help="Confirm the rollback")
    p_hist_rollback.set_defaults(func=cmd_history_rollback)

    p_doctor = subparsers.add_parser("doctor", help="Environment/self-check")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.set_defaults(func=cmd_doctor)

    p_ui = subparsers.add_parser("ui", help="Launch the local browser UI")
    p_ui.add_argument("--port", type=int, default=0, help="TCP port (0 = pick a free port)")
    p_ui.add_argument("--no-browser", action="store_true", help="Do not auto-open a browser tab")
    p_ui.set_defaults(func=cmd_ui)

    p_hpe = subparsers.add_parser("hpe", help="Uniden .hpe/.hpd container/record engine")
    hpe_sub = p_hpe.add_subparsers(dest="hpe_command", required=True)

    p_hpe_decode = hpe_sub.add_parser("decode", help=".hpe bytes -> plain tab-delimited text")
    p_hpe_decode.add_argument("file")
    p_hpe_decode.add_argument("--out", help="Write text here instead of stdout")
    p_hpe_decode.add_argument("--max-size", type=int, default=hpe_codec.DEFAULT_MAX_DECOMPRESSED_SIZE)
    p_hpe_decode.set_defaults(func=cmd_hpe_decode)

    p_hpe_encode = hpe_sub.add_parser("encode", help="plain tab-delimited text -> .hpe bytes")
    p_hpe_encode.add_argument("file")
    p_hpe_encode.add_argument("--out", required=True)
    p_hpe_encode.set_defaults(func=cmd_hpe_encode)

    p_hpe_inspect = hpe_sub.add_parser("inspect", help="Show dialect + hierarchy of a .hpe/.hpd file")
    p_hpe_inspect.add_argument("file")
    p_hpe_inspect.add_argument("--max-size", type=int, default=hpe_codec.DEFAULT_MAX_DECOMPRESSED_SIZE)
    p_hpe_inspect.add_argument("--json", action="store_true")
    p_hpe_inspect.set_defaults(func=cmd_hpe_inspect)

    p_hpe_validate = hpe_sub.add_parser("validate", help="Arity-validate a .hpe/.hpd file against the BCDx36HP schema")
    p_hpe_validate.add_argument("file")
    p_hpe_validate.add_argument("--max-size", type=int, default=hpe_codec.DEFAULT_MAX_DECOMPRESSED_SIZE)
    p_hpe_validate.add_argument("--json", action="store_true")
    p_hpe_validate.set_defaults(func=cmd_hpe_validate)

    p_hpe_build = hpe_sub.add_parser("build", help="Build a .hpe/.hpd file from canonical System JSON")
    p_hpe_build.add_argument("--systems", required=True, help='JSON file: {"systems": [...]} or a bare list')
    p_hpe_build.add_argument("--out", required=True, help="Output path; .hpe encodes, anything else writes plain text")
    p_hpe_build.add_argument("--force", action="store_true", help="Write even if schema validation finds issues")
    p_hpe_build.set_defaults(func=cmd_hpe_build)

    p_hpe_hpdb_inspect = hpe_sub.add_parser(
        "hpdb-inspect", help="Read-only: list states/counties (hpdb.cfg) or systems (s_<state>.hpd)"
    )
    p_hpe_hpdb_inspect.add_argument("file")
    p_hpe_hpdb_inspect.add_argument("--json", action="store_true")
    p_hpe_hpdb_inspect.set_defaults(func=cmd_hpe_hpdb_inspect)

    p_hpe_hpdb_extract = hpe_sub.add_parser(
        "hpdb-extract", help="Extract systems from a s_<state>.hpd by county or radius, converted to Favorites dialect"
    )
    p_hpe_hpdb_extract.add_argument("file", help="s_<state>.hpd HPDB system file")
    p_hpe_hpdb_extract.add_argument("--county-id", type=int, help="Keep only systems covering this CountyId")
    p_hpe_hpdb_extract.add_argument("--within", help="Keep only systems within 'LAT,LON,RADIUS_MILES'")
    p_hpe_hpdb_extract.add_argument("--no-dqks", action="store_true", help="Do not synthesize DQKs_Status")
    p_hpe_hpdb_extract.add_argument("--out", required=True, help="Output path; .hpe encodes, anything else writes plain text")
    p_hpe_hpdb_extract.set_defaults(func=cmd_hpe_hpdb_extract)

    p_merge = subparsers.add_parser("merge", help="Three-way merge: current catalog + upstream + profile")
    merge_sub = p_merge.add_subparsers(dest="merge_command", required=True)

    p_merge_preview = merge_sub.add_parser("preview", help="Show merge changes/conflicts without applying")
    p_merge_preview.add_argument("--upstream", required=True, help="Upstream catalog CSV or JSON file")
    p_merge_preview.add_argument("--json", action="store_true")
    p_merge_preview.set_defaults(func=cmd_merge_preview)

    p_merge_apply = merge_sub.add_parser("apply", help="Apply the merge: persist the merged catalog + profile")
    p_merge_apply.add_argument("--upstream", required=True, help="Upstream catalog CSV or JSON file")
    p_merge_apply.add_argument("--force", action="store_true", help="Apply even if conflicts are found")
    p_merge_apply.add_argument("--json", action="store_true")
    p_merge_apply.set_defaults(func=cmd_merge_apply)

    p_sources = subparsers.add_parser("sources", help="Online/local source adapters: list/configure/fetch/update")
    sources_sub = p_sources.add_subparsers(dest="sources_command", required=True)

    p_sources_list = sources_sub.add_parser("list", help="List known source adapters")
    p_sources_list.add_argument("--json", action="store_true")
    p_sources_list.set_defaults(func=cmd_sources_list)

    p_sources_status = sources_sub.add_parser("status", help="Show cache freshness per source")
    p_sources_status.add_argument("--json", action="store_true")
    p_sources_status.set_defaults(func=cmd_sources_status)

    p_sources_configure = sources_sub.add_parser(
        "configure", help="Set offline mode and local-file paths (Sentinel HPDB / RadioReference export)"
    )
    p_sources_configure.add_argument("--online", action="store_true", help="Disable offline mode")
    p_sources_configure.add_argument("--offline", action="store_true", help="Enable offline mode (serve cache only)")
    p_sources_configure.add_argument("--sentinel-mount", help="Path to a mounted/copied SDS150 card")
    p_sources_configure.add_argument("--sentinel-hpdb-cfg", help="Path directly to an hpdb.cfg file")
    p_sources_configure.add_argument("--rr-export-path", help="Path to a user-exported RR Premium CSV/XML file")
    p_sources_configure.add_argument("--rr-username", help="RadioReference username (non-secret identifier only)")
    p_sources_configure.add_argument("--rr-app-key", help="RadioReference app key (never a password)")
    p_sources_configure.add_argument("--json", action="store_true")
    p_sources_configure.set_defaults(func=cmd_sources_configure)

    p_sources_fetch = sources_sub.add_parser("fetch", help="Fetch+normalize a single source (no merge)")
    p_sources_fetch.add_argument("name", help="Source adapter name, e.g. wwara")
    p_sources_fetch.add_argument("--json", action="store_true")
    p_sources_fetch.set_defaults(func=cmd_sources_fetch)

    p_sources_update = sources_sub.add_parser(
        "update", help="Run all configured sources, enrich + three-way-merge against the current catalog"
    )
    p_sources_update.add_argument("--only", help="Comma-separated subset of source names to run")
    p_sources_update.add_argument("--offline", action="store_true", help="Force offline mode for this run")
    p_sources_update.add_argument("--apply", action="store_true", help="Persist the merge (default: preview only)")
    p_sources_update.add_argument("--force", action="store_true", help="Apply even if conflicts are found")
    p_sources_update.add_argument("--json", action="store_true")
    p_sources_update.set_defaults(func=cmd_sources_update)

    p_sources_provenance = sources_sub.add_parser("provenance", help="Show provenance for one favorite")
    p_sources_provenance.add_argument("slug", help="Favorite slug, e.g. fl04")
    p_sources_provenance.add_argument("--json", action="store_true")
    p_sources_provenance.set_defaults(func=cmd_sources_provenance)

    p_install = subparsers.add_parser(
        "install", help="EXPERIMENTAL: direct SD-card installer (detect/backup/write/rollback)"
    )
    install_sub = p_install.add_subparsers(dest="install_command", required=True)

    p_install_detect = install_sub.add_parser("detect", help="Find candidate SDS150 removable volumes")
    p_install_detect.add_argument("--dir", action="append", help="Check this directory instead of OS auto-detection (repeatable)")
    p_install_detect.add_argument("--json", action="store_true")
    p_install_detect.set_defaults(func=cmd_install_detect)

    p_install_backup = install_sub.add_parser("backup", help="Back up a card's BCDx36HP tree")
    p_install_backup.add_argument("mount", help="Card mount point")
    p_install_backup.add_argument("--out-dir", required=True, help="Directory to write the backup zip into")
    p_install_backup.add_argument("--json", action="store_true")
    p_install_backup.set_defaults(func=cmd_install_backup)

    p_install_write = install_sub.add_parser(
        "write",
        help="Write a Favorites List to a card: default workflow is profile -> generated favorites (--slug); "
        "--systems is a raw-JSON advanced/debug path. Dry-run by default; --execute + --confirm to write for real.",
    )
    p_install_write.add_argument("mount", help="Card mount point")
    p_install_write.add_argument(
        "--slug", help="Favorite_key/slug of a generated Favorites List to install (default workflow)"
    )
    p_install_write.add_argument(
        "--systems", help='ADVANCED/DEBUG: JSON file: {"systems": [...]} or a bare list, instead of --slug'
    )
    p_install_write.add_argument("--index", type=int, required=True, help="Favorites list slot index (0-255)")
    p_install_write.add_argument(
        "--user-name", help="Favorites List display name (defaults to the generated favorite_name with --slug)"
    )
    p_install_write.add_argument("--backup-dir", required=True, help="Where the mandatory pre-write backup is stored")
    p_install_write.add_argument("--confirm", help="Typed confirmation phrase (required with --execute)")
    p_install_write.add_argument("--execute", action="store_true", help="Actually write (default: dry-run only)")
    p_install_write.add_argument("--json", action="store_true")
    p_install_write.set_defaults(func=cmd_install_write)


    p_install_rollback = install_sub.add_parser("rollback", help="Restore a card from a prior backup")
    p_install_rollback.add_argument("mount", help="Card mount point")
    p_install_rollback.add_argument("--backup", required=True, help="Backup zip produced by 'install backup'/'install write'")
    p_install_rollback.add_argument("--json", action="store_true")
    p_install_rollback.set_defaults(func=cmd_install_rollback)

    p_install_hpdb_inspect = install_sub.add_parser(
        "hpdb-inspect", help="Read-only: list states/counties/systems found in a card's HPDB/ tree"
    )
    p_install_hpdb_inspect.add_argument("mount", help="Card mount point")
    p_install_hpdb_inspect.add_argument("--json", action="store_true")
    p_install_hpdb_inspect.set_defaults(func=cmd_install_hpdb_inspect)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:  # pragma: no cover - top-level safety net
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
