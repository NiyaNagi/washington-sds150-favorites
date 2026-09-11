"""The one-click fleet update.

Refresh the sources that are stale (each one skippable), merge what they
found into the catalog, then bring every selected radio up to date: resolve
its plan, compare with the last snapshot, export, load, verify, snapshot and
record the sync so the radio stops showing as stale.

Loading depends on the radio (see :mod:`wasds150.fleet.registry`). The SDS150
and TD-H9 are loaded automatically; the TH-D75, FTX-1 and AT-D890UV are
*prepared and guided* - the wizard exports, opens the vendor program and then
waits at each step that needs a click, with Done / Skip / Abort.

Without ``execute`` the update is a dry run: every radio is resolved and
exported (and the SDS150 install is planned), and nothing touches hardware or
a Sentinel workspace. Writes additionally need the typed confirmations the
rest of the project uses (``WRITE COM7``, ``IMPORT <profile>``).

Everything that reaches outside the process - fetching sources, launching a
vendor program, driving the CHIRP programmer, writing the Sentinel workspace -
goes through :class:`UpdateHooks`, so the whole flow runs in tests with fakes.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from wasds150.appctx import AppContext
from wasds150.fleet.model import LOAD_AUTOMATED, STEP_AUTO, STEP_MANUAL, FleetRadio, StepSpec, render_instructions
from wasds150.fleet.registry import get_fleet_radio
from wasds150.fleet.service import export_radio, load_settings, record_sync, scanner_favorites, scanner_list_settings
from wasds150.jobs.context import JobContext, StepHandle, StepSkipped
from wasds150.jobs.events import CATALOG_DELTA, DECISION_SKIP, RADIO_DIFF
from wasds150.jobs.runner import JobCancelled, JobRunner
from wasds150.plan.service import DEFAULT_OUT_DIR

JOB_KIND = "fleet-update"

#: Checklist steps after which the radio holds the new memories.
_WRITE_STEPS = frozenset({"write-radio", "send-to-radio"})


# ------------------------------------------------------------------- spec --
@dataclass
class FleetUpdateSpec:
    radio_ids: List[str] = field(default_factory=list)
    refresh_sources: bool = True
    #: Sources to refresh; ``None`` means "every configured source whose
    #: cache is stale".
    only_sources: Optional[List[str]] = None
    skip_sources: List[str] = field(default_factory=list)
    apply_sources: bool = True
    force_conflicts: bool = False
    refresh_contacts: bool = True
    include_licensed: bool = True
    execute: bool = False
    #: Skip the vendor-program checklist items (confirmations and typed
    #: inputs are still asked for).
    skip_manual: bool = False
    launch_apps: bool = True
    out_dir: str = DEFAULT_OUT_DIR
    copy_to: Dict[str, str] = field(default_factory=dict)
    #: ``{radio_id: {input_id: value}}`` on top of the saved fleet settings.
    inputs: Dict[str, Dict[str, str]] = field(default_factory=dict)
    #: Filled in by :meth:`JobRunner.resume`.
    completed_steps: List[str] = field(default_factory=list)
    completed_data: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def validate(self) -> "FleetUpdateSpec":
        if not self.radio_ids:
            raise ValueError("choose at least one radio")
        seen: List[str] = []
        for radio_id in self.radio_ids:
            canonical = get_fleet_radio(radio_id).radio_id  # KeyError for an unknown radio
            if canonical not in seen:
                seen.append(canonical)
        self.radio_ids = seen
        return self

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FleetUpdateSpec":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in (data or {}).items() if k in known})


# ------------------------------------------------------------------ hooks --
def _default_fetch(ctx: AppContext, names: List[str]) -> Any:
    from wasds150.sources.config import SourcesConfig
    from wasds150.sources.factory import build_http_client, instantiate_source
    from wasds150.update.pipeline import run_sources

    sources_config = SourcesConfig.load(ctx.config.sources_config_path)
    instances = [s for s in (instantiate_source(n, sources_config) for n in names) if s is not None]
    return run_sources(instances, http_client=build_http_client(ctx.config, sources_config.offline))


def _default_launch(exe: Path, args: List[str]) -> None:
    flags = 0
    if os.name == "nt":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    subprocess.Popen([str(exe), *args], close_fds=True, creationflags=flags)  # noqa: S603 - argv vector


def _default_program_tdh9(*, port: str, csv_path: Path, label: str, execute: bool,
                          on_line: Callable[[str], None], should_cancel: Callable[[], bool]) -> Any:
    from wasds150.radios import programmer

    argv = programmer.build_command(port=port, csv_path=csv_path, label=label, execute=execute)
    return programmer.run_streaming(argv, on_line, should_cancel=should_cancel)


def _default_install(*args: Any, **kwargs: Any) -> Any:
    from wasds150.installer.sentinel_workspace import install_selected_favorites

    return install_selected_favorites(*args, **kwargs)


def _default_refresh_contacts(ctx: AppContext, job: JobContext) -> str:
    from wasds150.contacts.refresh import refresh_contacts

    return refresh_contacts(ctx, job)


@dataclass
class UpdateHooks:
    fetch: Callable[..., Any] = _default_fetch
    launch: Callable[[Path, List[str]], None] = _default_launch
    program_tdh9: Callable[..., Any] = _default_program_tdh9
    install_sentinel: Callable[..., Any] = _default_install
    refresh_contacts: Callable[[AppContext, JobContext], str] = _default_refresh_contacts


# ---------------------------------------------------------------- sources --
def source_choices(ctx: AppContext) -> List[Dict[str, Any]]:
    """Every runnable source with whether it is configured and stale."""
    from wasds150.cache.store import HttpCacheStore
    from wasds150.sources.config import SourcesConfig
    from wasds150.sources.factory import instantiate_source, runnable_source_names
    from wasds150.sources.registry import get_source_class

    sources_config = SourcesConfig.load(ctx.config.sources_config_path)
    store = HttpCacheStore(ctx.config.cache_dir)
    rows = []
    for name in runnable_source_names():
        configured = instantiate_source(name, sources_config) is not None
        entries = store.entries_for_source(name)
        stale = configured and (not entries or not all(entry.is_fresh() for entry in entries))
        rows.append(
            {
                "name": name,
                "configured": configured,
                "stale": stale,
                "bulk": bool(getattr(get_source_class(name), "bulk", False)),
                "cached_urls": len(entries),
                "last_fetch": max((entry.fetched_at for entry in entries), default=None),
            }
        )
    return rows


def selected_sources(ctx: AppContext, spec: FleetUpdateSpec) -> List[str]:
    if not spec.refresh_sources:
        return []
    rows = source_choices(ctx)
    if spec.only_sources is not None:
        chosen = [r["name"] for r in rows if r["name"] in spec.only_sources and r["configured"]]
    else:
        # Bulk downloads (hundreds of MB) are never refreshed implicitly.
        chosen = [r["name"] for r in rows if r["stale"] and not r["bulk"]]
    return [name for name in chosen if name not in spec.skip_sources]


def _apply_facts(ctx: AppContext, spec: FleetUpdateSpec, facts: List[Any], reason: str) -> Any:
    from wasds150.merge.three_way import apply_merge
    from wasds150.update.pipeline import build_and_merge

    with ctx.lock:
        profile = ctx.load_profile()
        merge = build_and_merge(ctx.catalog, profile, facts)["merge"]
        if merge.conflicts and not spec.force_conflicts:
            raise RuntimeError(f"{len(merge.conflicts)} conflict(s); run again with conflicts forced to apply anyway")
        new_profile = apply_merge(profile, merge)
        delta = ctx.save_catalog(merge.merged_catalog, reason=reason)
        ctx.save_profile(new_profile)
    return delta


def _refresh_sources(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                     summary: Dict[str, Any]) -> None:
    if job.completed("sources.merge") is not None:
        job.skip("sources.merge", "Merge into the catalog", "merged in the resumed job")
        return
    chosen = set(selected_sources(ctx, spec))
    facts: List[Any] = []
    refreshed: List[str] = []
    for row in source_choices(ctx):
        name = row["name"]
        step_id, title = f"sources.{name}", f"Refresh {name}"
        if name not in chosen:
            if name in spec.skip_sources:
                reason = "skipped"
            elif not row["configured"]:
                reason = "not configured"
            elif spec.only_sources is not None:
                reason = "not selected"
            elif row["bulk"] and row["stale"]:
                reason = "large download: refreshed only when selected"
            else:
                reason = "fresh in the cache"
            job.skip(step_id, title, reason, optional=True)
            summary["sources"][name] = reason
            continue
        try:
            with job.step(step_id, title, optional=True) as handle:
                run = hooks.fetch(ctx, [name])
                outcome = run.outcomes[0] if run.outcomes else None
                if outcome is None:
                    raise StepSkipped("not configured")
                for warning in outcome.warnings[:20]:
                    job.log(warning)
                if not outcome.ok:
                    raise RuntimeError(outcome.error or "fetch failed")
                facts.extend(run.facts)
                refreshed.append(name)
                handle.message = f"{outcome.fact_count} facts, {outcome.alert_count} alerts"
            summary["sources"][name] = "ok"
        except JobCancelled:
            raise
        except Exception as exc:  # noqa: BLE001 - one flaky source never stops the update
            summary["sources"][name] = f"failed: {exc}"

    if not facts:
        job.skip("sources.merge", "Merge into the catalog", "no new facts")
        return
    if not spec.apply_sources:
        job.skip("sources.merge", "Merge into the catalog", "preview only: applying is turned off")
        return
    try:
        with job.step("sources.merge", "Merge into the catalog") as handle:
            delta = _apply_facts(ctx, spec, facts, reason="fleet update: " + ", ".join(refreshed))
            handle.message = delta.summary()
            handle.data["update_id"] = delta.id
            payload = delta.to_dict()
            payload["per_slug"] = payload["per_slug"][:50]
            job.emit(CATALOG_DELTA, delta.summary(), data=payload)
            summary["catalog"] = delta.summary()
    except JobCancelled:
        raise
    except Exception as exc:  # noqa: BLE001 - radios are still built from the current catalog
        summary["catalog"] = f"not applied: {exc}"


def _refresh_contacts(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                      summary: Dict[str, Any]) -> None:
    from wasds150.radios.registry import get_profile

    if not any(get_profile(r).contacts for r in spec.radio_ids):
        return
    title = "Refresh DMR/NXDN contacts"
    if not spec.refresh_contacts:
        job.skip("contacts.refresh", title, "turned off", optional=True)
        return
    try:
        with job.step("contacts.refresh", title, optional=True) as handle:
            handle.message = hooks.refresh_contacts(ctx, job)
        summary["contacts"] = "ok"
    except JobCancelled:
        raise
    except Exception as exc:  # noqa: BLE001 - radios still load without fresh contacts
        summary["contacts"] = f"failed: {exc}"


# ----------------------------------------------------------------- radios --
def _checklist_step(job: JobContext, spec: FleetUpdateSpec, prefix: str, step: StepSpec,
                    context: Dict[str, Any]) -> bool:
    """Show one checklist item and wait; True when the operator did it."""
    step_id = f"{prefix}.{step.id}"
    if spec.skip_manual and step.kind == STEP_MANUAL:
        job.skip(step_id, step.title, "manual steps skipped", optional=step.optional)
        return False
    done = {"ok": False}
    artifacts = {k: str(context[k]) for k in ("export", "lst", "contacts", "final", "report") if context.get(k)}
    with job.step(step_id, step.title, optional=step.optional) as handle:
        answer = job.wait_for_user(render_instructions(step.instructions, context), kind=step.kind, artifacts=artifacts)
        if answer.decision == DECISION_SKIP:
            raise StepSkipped("skipped by the operator")
        handle.message = "done"
        done["ok"] = True
    return done["ok"]


def _skip_rest(job: JobContext, prefix: str, steps: List[StepSpec], reason: str) -> None:
    for step in steps:
        job.skip(f"{prefix}.{step.id}", step.title, reason, optional=step.optional)


def _load_sds150(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                 radio: FleetRadio, context: Dict[str, Any], values: Dict[str, str]) -> Tuple[bool, bool]:
    from wasds150.installer.sentinel_workspace import confirmation_phrase

    prefix = f"radio.{radio.radio_id}"
    close, install, reopen = radio.step("close-sentinel"), radio.step("install"), radio.step("reopen-sentinel")
    if spec.execute:
        if not _checklist_step(job, spec, prefix, close, context):
            _skip_rest(job, prefix, [install, reopen], "Sentinel was not confirmed closed")
            return False, False
    else:
        job.skip(f"{prefix}.{close.id}", close.title, "dry run")

    result = {"loaded": False, "verified": False}
    with job.step(f"{prefix}.{install.id}", install.title) as handle:
        workspace = Path(os.path.expandvars(values.get("sentinel_workspace") or ""))
        profile_name = job.require_input(radio.input("sentinel_profile").to_dict(), values.get("sentinel_profile", ""))
        if not profile_name:
            raise StepSkipped("no Sentinel profile given")
        context["sentinel_profile"] = profile_name
        favorites = scanner_favorites(ctx, include_licensed=spec.include_licensed)
        if not favorites:
            raise StepSkipped("no enabled, populated Favorites Lists")
        backup_dir = ctx.config.backup_dir / "sentinel-workspace"
        settings = scanner_list_settings(favorites)
        planned = hooks.install_sentinel(
            workspace, profile_name, favorites, backup_dir=backup_dir, execute=False, allow_replacements=True,
            list_settings=settings,
        )
        for warning in planned.warnings:
            job.log(warning)
        handle.data["planned"] = len(planned.assignments)
        if not spec.execute:
            handle.message = f"dry run: {len(planned.assignments)} list(s) would be installed into {profile_name}"
        else:
            phrase = confirmation_phrase(profile_name)
            typed = job.require_input(
                {"id": "confirm", "kind": "text", "label": f"Type {phrase}",
                 "help": f"Type {phrase} to install {len(planned.assignments)} list(s) into {profile_name}."}
            )
            if typed != phrase:
                raise StepSkipped("confirmation did not match; nothing was installed")
            done = hooks.install_sentinel(
                workspace, profile_name, favorites, backup_dir=backup_dir, execute=True,
                confirm=typed, expected_plan_id=planned.plan_id, allow_replacements=True,
                list_settings=settings,
            )
            handle.data["backup"] = str(done.backup_path or "")
            if done.outcome != "committed":
                raise RuntimeError(f"install {done.outcome}; backup at {done.backup_path}")
            handle.message = f"installed {len(done.assignments)} list(s)"
            result.update(loaded=True, verified=bool(done.verified))

    if result["loaded"]:
        _checklist_step(job, spec, prefix, reopen, context)
    else:
        _skip_rest(job, prefix, [reopen], "nothing was installed")
    return result["loaded"], result["verified"]


def _load_tdh9(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
               radio: FleetRadio, context: Dict[str, Any], values: Dict[str, str]) -> Tuple[bool, bool]:
    from wasds150.radios import programmer

    prefix = f"radio.{radio.radio_id}"
    connect, backup, flash, cycle = (radio.step(s) for s in ("connect", "backup", "flash", "power-cycle"))
    if not spec.execute:
        _skip_rest(job, prefix, [connect, backup, flash, cycle], "dry run: the radio is not touched")
        return False, False
    if not _checklist_step(job, spec, prefix, connect, context):
        _skip_rest(job, prefix, [backup, flash, cycle], "the radio was not connected")
        return False, False

    port_holder = {"port": ""}
    with job.step(f"{prefix}.{backup.id}", backup.title) as handle:
        port = programmer.validate_port(
            job.require_input(radio.input("com_port").to_dict(), values.get("com_port", ""))
        )
        port_holder["port"] = port
        context["com_port"] = port
        run = hooks.program_tdh9(
            port=port, csv_path=Path(context["export"]), label=programmer.validate_label(values.get("label") or "td-h9"),
            execute=False, on_line=job.log, should_cancel=job.cancelled,
        )
        job.check_cancelled()
        if not run.ok:
            raise RuntimeError(f"programmer exited {run.returncode}: {run.stderr or 'see the log'}")
        handle.message = "backed up; the file stages cleanly"

    result = {"loaded": False}
    with job.step(f"{prefix}.{flash.id}", flash.title) as handle:
        phrase = f"WRITE {port_holder['port']}"
        typed = job.require_input(
            {"id": "confirm", "kind": "text", "label": f"Type {phrase}",
             "help": f"Type {phrase} to overwrite every memory on the radio (a backup was just taken)."}
        )
        if typed != phrase:
            raise StepSkipped("confirmation did not match; nothing was written")
        run = hooks.program_tdh9(
            port=port_holder["port"], csv_path=Path(context["export"]),
            label=programmer.validate_label(values.get("label") or "td-h9"),
            execute=True, on_line=job.log, should_cancel=job.cancelled,
        )
        job.check_cancelled()
        if not run.ok:
            raise RuntimeError(f"programmer exited {run.returncode}: {run.stderr or 'see the log'}")
        handle.message = "written and read back"
        result["loaded"] = True

    if result["loaded"]:
        _checklist_step(job, spec, prefix, cycle, context)
    else:
        _skip_rest(job, prefix, [cycle], "nothing was written")
    # program_tdh9.py reads the radio back after every write and exits
    # non-zero on any difference, so a clean write is a verified one.
    return result["loaded"], result["loaded"]


def _open_vendor_app(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                     radio: FleetRadio, context: Dict[str, Any], values: Dict[str, str], handle: StepHandle) -> None:
    app = radio.vendor_app
    if app is None:
        raise StepSkipped("no vendor program for this radio")
    override = next((values.get(s.id, "") for s in radio.inputs if s.kind == "app_path"), "")
    exe = app.find(override)
    if exe is None:
        handle.message = f"{app.label} not found; open it yourself"
        return
    if not spec.launch_apps:
        handle.message = f"found {exe}; launching is turned off"
        return
    hooks.launch(exe, [str(context["export"])] if app.open_with_file else [])
    handle.message = f"started {exe.name}"


def _finalize_thd75(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                    radio: FleetRadio, context: Dict[str, Any], values: Dict[str, str], handle: StepHandle) -> None:
    from wasds150.export.thd75_target import restore_unowned_regions, template_path

    backup = values.get("backup_d75") or str(template_path())
    saved = job.require_input(
        {"id": "mcp_saved", "kind": "file", "label": "File saved from MCP-D75",
         "help": "The full path of the file you saved from MCP-D75 in the previous step."},
        values.get("mcp_saved", ""),
    )
    if not saved:
        raise StepSkipped("no MCP-saved file given")
    data, restored = restore_unowned_regions(Path(saved).read_bytes(), Path(backup).read_bytes())
    export = Path(context["export"])
    final = export.with_name(f"{export.stem}-final{export.suffix}")
    final.write_bytes(data)
    handle.artifact("final", final)
    context["final"] = str(final)
    handle.message = f"restored {restored} byte(s) from {Path(backup).name} -> {final.name}"


def _diff_readback(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                   radio: FleetRadio, context: Dict[str, Any], values: Dict[str, str], handle: StepHandle) -> None:
    try:
        from wasds150.export.atd890_diff import compare_bundle
    except ImportError:
        raise StepSkipped("the read-back comparison is not available in this build") from None
    readback = job.require_input(
        {"id": "readback_dir", "kind": "dir", "label": "Read-back Export All folder",
         "help": "The folder the CPS's Export All wrote after reading the radio back."},
        values.get("readback_dir", ""),
    )
    if not readback:
        raise StepSkipped("no read-back folder given")
    diff = compare_bundle(Path(context["export"]), Path(readback))
    handle.data["diff"] = diff.to_dict()
    if not diff.clean:
        raise RuntimeError(diff.summary())
    context["verified"] = True
    handle.message = "the read-back matches the bundle"


_AUTO_HANDLERS: Dict[str, Callable[..., None]] = {
    "open-mcp": _open_vendor_app,
    "open-rt": _open_vendor_app,
    "open-cps": _open_vendor_app,
    "finalize": _finalize_thd75,
    "diff-readback": _diff_readback,
}


def _load_guided(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                 radio: FleetRadio, context: Dict[str, Any], values: Dict[str, str]) -> Tuple[bool, bool]:
    prefix = f"radio.{radio.radio_id}"
    steps = [step for step in radio.steps if step.id != "export"]
    if not spec.execute:
        _skip_rest(job, prefix, steps, "dry run: the file is prepared; run with execute to walk through loading it")
        return False, False
    loaded = False
    for step in steps:
        step_id = f"{prefix}.{step.id}"
        if step.kind == STEP_AUTO:
            handler = _AUTO_HANDLERS.get(step.id)
            if handler is None:
                job.skip(step_id, step.title, "nothing to run", optional=step.optional)
                continue
            try:
                with job.step(step_id, step.title, optional=step.optional) as handle:
                    handler(ctx, spec, job, hooks, radio, context, values, handle)
            except JobCancelled:
                raise
            except Exception:  # noqa: BLE001 - an optional helper step never stops the checklist
                if not step.optional:
                    raise
            continue
        if _checklist_step(job, spec, prefix, step, context) and step.id in _WRITE_STEPS:
            loaded = True
    return loaded, bool(context.get("verified"))


def _update_radio(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext, hooks: UpdateHooks,
                  radio: FleetRadio) -> Dict[str, Any]:
    from wasds150.plan.loadout import diff_against_snapshot, save_snapshot
    from wasds150.plan.service import resolve_named_plan
    from wasds150.plans.template import default_knobs
    from wasds150.radios.registry import get_profile

    label = get_profile(radio.radio_id).label
    prefix = f"radio.{radio.radio_id}"
    loadout_id = radio.plan_id or radio.radio_id
    values = load_settings(ctx).values_for(radio)
    values.update({k: v for k, v in spec.inputs.get(radio.radio_id, {}).items() if v})
    context: Dict[str, Any] = dict(values)
    context.update(plan_id=radio.plan_id, callsign=default_knobs(radio.radio_id).callsign)
    result: Dict[str, Any] = {"exported": None, "loaded": False, "verified": False, "recorded": False}

    if radio.plan_id:
        with job.step(f"{prefix}.resolve", f"{label}: resolve {radio.plan_id}") as handle:
            _plan, resolved = resolve_named_plan(ctx, radio.plan_id, include_licensed=spec.include_licensed)
            transmit = sum(1 for c in resolved.channels if c.transmit)
            handle.message = (
                f"{resolved.slots_used} of {resolved.capacity} slots, {transmit} transmit, "
                f"{len(resolved.warnings)} warning(s)"
            )
            handle.data.update(slots=resolved.slots_used, capacity=resolved.capacity, transmit=transmit,
                               drop_reasons=resolved.drop_reasons())

    with job.step(f"{prefix}.diff", f"{label}: compare with the last snapshot") as handle:
        diff = diff_against_snapshot(ctx, loadout_id)
        if diff.get("has_snapshot"):
            handle.message = f"+{diff.get('added', 0)} -{diff.get('removed', 0)} since {diff.get('saved_at', '')}"
        else:
            handle.message = str(diff.get("message", "no snapshot yet"))
        job.emit(RADIO_DIFF, handle.message, data={
            "radio_id": radio.radio_id, "has_snapshot": bool(diff.get("has_snapshot")),
            "added": diff.get("added"), "removed": diff.get("removed"),
        })

    export_id = f"{prefix}.export"
    prior = job.completed(export_id)
    if prior and (prior.get("artifacts") or {}).get("export"):
        artifact = prior["artifacts"]["export"]
        context.update(export=artifact["path"], lst=prior.get("lst", ""), rows=prior.get("rows", 0),
                       report=prior.get("report", ""), contacts=prior.get("contacts", ""))
        export_sha = artifact["sha256"]
        job.skip(export_id, f"{label}: export", f"reused {artifact['path']} from the resumed job")
    else:
        with job.step(export_id, f"{label}: export") as handle:
            copy_to = spec.copy_to.get(radio.radio_id) or values.get("copy_to") or ""
            export = export_radio(ctx, radio.radio_id, out_dir=Path(spec.out_dir),
                                  copy_to=Path(copy_to) if copy_to else None,
                                  include_licensed=spec.include_licensed)
            handle.artifact("export", export.path)
            lst = next((str(f) for f in export.files if f.suffix.upper() == ".LST"), "")
            contacts = next((str(f) for f in export.files if f.name.upper().startswith("DIGITALCONTACTLIST")), "")
            handle.data.update(rows=export.rows, report=str(export.report_path or ""), lst=lst, contacts=contacts,
                               copies=len(export.copies), warnings=len(export.warnings))
            handle.message = f"{export.rows} rows -> {export.path}"
            context.update(export=str(export.path), lst=lst, rows=export.rows, report=str(export.report_path or ""),
                           contacts=contacts)
        export_sha = job._job.status.step(export_id).data["artifacts"]["export"]["sha256"]
    result["exported"] = context["export"]

    if radio.radio_id == "sds150":
        loaded, verified = _load_sds150(ctx, spec, job, hooks, radio, context, values)
    elif radio.load_path == LOAD_AUTOMATED:
        loaded, verified = _load_tdh9(ctx, spec, job, hooks, radio, context, values)
    else:
        loaded, verified = _load_guided(ctx, spec, job, hooks, radio, context, values)
    result.update(loaded=loaded, verified=verified)

    if not loaded:
        reason = "dry run: nothing was written" if not spec.execute else "the radio was not written"
        for suffix, title in (("verify", "verify"), ("snapshot", "save a snapshot"), ("record", "record the sync")):
            job.skip(f"{prefix}.{suffix}", f"{label}: {title}", reason)
        return result

    with job.step(f"{prefix}.verify", f"{label}: verify") as handle:
        handle.message = "verified" if verified else f"not verified ({radio.verify})"
    with job.step(f"{prefix}.snapshot", f"{label}: save a snapshot") as handle:
        snapshot = save_snapshot(ctx, loadout_id)
        handle.message = str(snapshot.get("path", ""))
    with job.step(f"{prefix}.record", f"{label}: record the sync") as handle:
        record_sync(ctx, radio.radio_id, job_id=job.job_id, export_sha256=export_sha,
                    loadout_snapshot_path=str(snapshot.get("path", "")), verified=verified)
        handle.message = "recorded; the radio is up to date"
    result["recorded"] = True
    return result


# -------------------------------------------------------------------- run --
def run_fleet_update(ctx: AppContext, spec: FleetUpdateSpec, job: JobContext,
                     hooks: Optional[UpdateHooks] = None) -> Dict[str, Any]:
    hooks = hooks or UpdateHooks()
    summary: Dict[str, Any] = {"sources": {}, "catalog": None, "radios": {}}
    if spec.refresh_sources:
        _refresh_sources(ctx, spec, job, hooks, summary)
    _refresh_contacts(ctx, spec, job, hooks, summary)
    failed = []
    for radio_id in spec.radio_ids:
        radio = get_fleet_radio(radio_id)
        try:
            summary["radios"][radio_id] = _update_radio(ctx, spec, job, hooks, radio)
        except JobCancelled:
            raise
        except Exception as exc:  # noqa: BLE001 - one radio's failure never stops the others
            summary["radios"][radio_id] = {"error": f"{type(exc).__name__}: {exc}"}
            failed.append(radio_id)
    if failed:
        # Failing the job keeps it resumable: a resume reuses every export
        # still on disk and picks up at the radio that stopped.
        raise RuntimeError(f"{len(failed)} radio(s) did not finish: {', '.join(failed)}")
    return summary


def fleet_update_title(spec: FleetUpdateSpec) -> str:
    mode = "update" if spec.execute else "dry run"
    return f"Fleet {mode}: {', '.join(spec.radio_ids)}"


def start_fleet_update(runner: JobRunner, ctx: AppContext, spec: FleetUpdateSpec,
                       hooks: Optional[UpdateHooks] = None) -> str:
    spec.validate()
    return runner.submit(
        JOB_KIND, fleet_update_title(spec), lambda job: run_fleet_update(ctx, spec, job, hooks), spec=spec.to_dict()
    )


def resume_fleet_update(runner: JobRunner, ctx: AppContext, job_id: str,
                        hooks: Optional[UpdateHooks] = None) -> str:
    def factory(data: Dict[str, Any]) -> Callable[[JobContext], Dict[str, Any]]:
        spec = FleetUpdateSpec.from_dict(data).validate()
        return lambda job: run_fleet_update(ctx, spec, job, hooks)

    return runner.resume(job_id, factory)
