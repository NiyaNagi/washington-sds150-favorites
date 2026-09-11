"""``wasds150 repeaterbook ...`` -- the only way the CLI reaches RepeaterBook.

Every command goes through :class:`wasds150.sources.repeaterbook.service.RepeaterBookService`,
which holds the guards. ``refresh`` is the one command that can send a
request, and only when the local enable flag is on, a token is set, and the
region, radius, band, rate-limit and lockout checks all pass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _print_json(data) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def _service(args: argparse.Namespace):
    from wasds150.cli import _build_config
    from wasds150.logging_setup import configure_logging
    from wasds150.sources.repeaterbook.service import RepeaterBookService

    config = _build_config(args)
    configure_logging(config.log_file)
    return RepeaterBookService(config)


def _run(args: argparse.Namespace, action) -> int:
    """Run ``action(service)``; report a refusal or failure as one line."""
    from wasds150.sources.repeaterbook.client import RepeaterBookError
    from wasds150.sources.repeaterbook.normalize import ResponseShapeError
    from wasds150.sources.repeaterbook.service import PolicyError
    from wasds150.sources.repeaterbook.store import ActionInProgress
    from wasds150.sources.repeaterbook.token import TokenError

    try:
        return action(_service(args))
    except (PolicyError, TokenError, RepeaterBookError, ActionInProgress, ResponseShapeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _csv(text: str):
    return tuple(part.strip() for part in (text or "").split(",") if part.strip())


def cmd_status(args: argparse.Namespace) -> int:
    def action(service) -> int:
        status = service.status()
        if args.json:
            _print_json(status)
            return 0
        print(f"RepeaterBook enabled: {status['enabled']}")
        if status["message"]:
            print(f"  {status['message']}")
        print(f"Token: {status['token_source'] or 'not configured'}"
              + (f" (fingerprint {status['token_fingerprint']})" if status["token_fingerprint"] else ""))
        if status["token_error"]:
            print(f"  token error: {status['token_error']}")
        print(f"Ready to refresh: {status['ready']}")
        print(f"Requests in the last 24 h: {status['requests_last_24h']} "
              f"({status['requests_remaining_24h']} remaining)")
        for block in status["blocks"]:
            print(f"  blocked ({block['kind']}) until {block['until'] or 'operator action'}: {block['reason']}")
        for region in status["regions"]:
            state = "enabled" if region["verified"] else "disabled"
            print(f"  {region['code']:3} {region['name']:18} {state:8} cache={region['cache']:5} last={region['last_fetch']}")
        print(f"Staged for review: {status['staged_pending']}; applied records: {status['applied_records']}")
        print(f"User-Agent: {status['user_agent']}")
        print(f"{status['attribution']['text']} <{status['attribution']['url']}>")
        return 0

    return _run(args, action)


def cmd_regions(args: argparse.Namespace) -> int:
    from wasds150.sources.repeaterbook.policy import REGIONS

    rows = [
        {"code": r.code, "name": r.name, "country": r.country, "state_id": r.state_id, "verified": r.verified, "note": r.note}
        for r in REGIONS.values()
    ]
    if args.json:
        _print_json({"regions": rows})
        return 0
    for row in rows:
        state = "enabled" if row["verified"] else "DISABLED"
        print(f"  {row['code']:3} {row['name']:18} {state:8} state_id={row['state_id'] or '-':4} {row['note']}")
    return 0


def cmd_configure(args: argparse.Namespace) -> int:
    def action(service) -> int:
        enabled = True if args.enable else False if args.disable else None
        status = service.configure(enabled=enabled, token_env=args.token_env, token_file=args.token_file)
        if args.json:
            _print_json(status)
            return 0
        print(f"RepeaterBook enabled: {status['enabled']}; token configured: {status['token_configured']}")
        if status["message"]:
            print(f"  {status['message']}")
        return 0

    return _run(args, action)


def cmd_forget_token(args: argparse.Namespace) -> int:
    def action(service) -> int:
        service.forget_token()
        print("Forgot where the RepeaterBook token is. Remove the environment variable or file yourself.")
        return 0

    return _run(args, action)


def cmd_refresh(args: argparse.Namespace) -> int:
    from wasds150.sources.repeaterbook.service import RefreshRequest, format_preview, parse_center

    def action(service) -> int:
        request = RefreshRequest(
            regions=_csv(args.regions),
            center=parse_center(args.center),
            radius_mi=args.radius_mi,
            bands=_csv(args.bands),
            radio_id=args.radio,
        )
        result = service.refresh(request, offline=args.offline)
        if args.json:
            _print_json(result)
            return 0
        print(format_preview(result), end="")
        print("Next: 'wasds150 repeaterbook review --report md', then 'wasds150 repeaterbook apply'.")
        return 0

    return _run(args, action)


def cmd_review(args: argparse.Namespace) -> int:
    from wasds150.sources.repeaterbook.service import format_preview

    def action(service) -> int:
        staged = service.staged(args.action)
        report = None
        if args.report:
            report = service.write_review_report(args.report, Path(args.out) if args.out else None, args.action)
        if args.json:
            _print_json(dict(staged, report=str(report) if report else None))
            return 0
        print(format_preview(staged), end="")
        if report:
            print(f"Wrote {report}")
        return 0

    return _run(args, action)


def cmd_apply(args: argparse.Namespace) -> int:
    def action(service) -> int:
        result = service.apply(args.action, include_flagged=args.include_flagged)
        if args.json:
            _print_json(result)
            return 0
        print(f"{result['attribution']['text']} <{result['attribution']['url']}>")
        print(f"Applied {result['applied']} record(s) from action {result['action_id']}.")
        for skip in result["skipped"]:
            print(f"  skipped {skip['rb_key']}: {skip['reason']}")
        print("Export them with 'wasds150 plan export <plan> --with-repeaterbook'.")
        return 0

    return _run(args, action)


def cmd_records(args: argparse.Namespace) -> int:
    def action(service) -> int:
        data = service.records()
        if args.json:
            _print_json(data)
            return 0
        print(f"{data['attribution']['text']} <{data['attribution']['url']}>")
        for r in data["records"]:
            print(f"  {r['rb_key']:>10}  {r.get('callsign', ''):8} {r['output_mhz']:.4f}  "
                  f"{r.get('city', '')}  retrieved {r['retrieved_at'][:10]}  {r['detail_url']}")
        return 0

    return _run(args, action)


def cmd_unblock(args: argparse.Namespace) -> int:
    def action(service) -> int:
        cleared = service.unblock_auth()
        print("Cleared the authentication block." if cleared else "No authentication block for this token.")
        return 0

    return _run(args, action)


def cmd_purge(args: argparse.Namespace) -> int:
    def action(service) -> int:
        counts = service.purge()
        _print_json(counts) if args.json else print(f"Purged: {counts}")
        return 0

    return _run(args, action)


def cmd_delete_all(args: argparse.Namespace) -> int:
    if not args.yes:
        print("error: Delete All RepeaterBook Data needs --yes", file=sys.stderr)
        return 1

    def action(service) -> int:
        counts = service.delete_all()
        if args.json:
            _print_json(counts)
            return 0
        print(f"Deleted all RepeaterBook data: {counts}. The token location is unchanged "
              "('wasds150 repeaterbook forget-token' removes it).")
        return 0

    return _run(args, action)


def add_parser(subparsers) -> None:
    from wasds150.sources.repeaterbook.policy import AMATEUR_BANDS, RADIUS_DEFAULT_MI

    p = subparsers.add_parser(
        "repeaterbook",
        help="RepeaterBook Export API: off by default, pending RepeaterBook approval",
    )
    sub = p.add_subparsers(dest="repeaterbook_command", required=True)

    def command(name: str, func, help_text: str, json_flag: bool = True):
        parser = sub.add_parser(name, help=help_text)
        if json_flag:
            parser.add_argument("--json", action="store_true")
        parser.set_defaults(func=func)
        return parser

    command("status", cmd_status, "Enable flag, token, budget, lockouts and cache freshness")
    command("regions", cmd_regions, "The region allowlist and which regions are enabled")

    p_conf = command("configure", cmd_configure, "Set the enable flag and where the token is (never the token)")
    group = p_conf.add_mutually_exclusive_group()
    group.add_argument("--enable", action="store_true", help="Allow live requests (only once RepeaterBook has approved)")
    group.add_argument("--disable", action="store_true", help="Refuse live requests (the default)")
    p_conf.add_argument("--token-env", help="Name of the environment variable holding your rbuapp_ token")
    p_conf.add_argument("--token-file", help="Absolute path, outside this repository, of a file holding the token")

    command("forget-token", cmd_forget_token, "Forget where the token is (separate from delete-all)", json_flag=False)

    p_refresh = command("refresh", cmd_refresh, "One explicit, guarded refresh")
    p_refresh.add_argument("--regions", required=True, help="Up to 3 allowlisted regions, e.g. WA or WA,OR")
    p_refresh.add_argument("--center", required=True, help="latitude,longitude of the one search centre")
    p_refresh.add_argument("--radius-mi", type=int, default=RADIUS_DEFAULT_MI, help="Whole miles, 1-60")
    p_refresh.add_argument("--bands", required=True, help=f"Comma-separated: {', '.join(AMATEUR_BANDS)}")
    p_refresh.add_argument("--radio", required=True, help="Target radio id, e.g. th-d75 (see 'radios list')")
    p_refresh.add_argument("--offline", action="store_true", help="Re-filter cached responses under 7 days old; no request")

    p_review = command("review", cmd_review, "Show staged candidates; optionally write a review report")
    p_review.add_argument("--action", help="Action id (default: the latest refresh)")
    p_review.add_argument("--report", choices=("md", "html"), help="Write a Markdown or HTML review report")
    p_review.add_argument("--out", help="Report path (default: the RepeaterBook store's reports folder)")

    p_apply = command("apply", cmd_apply, "Apply reviewed candidates to the local applied records")
    p_apply.add_argument("--action", help="Action id (default: the latest refresh)")
    p_apply.add_argument("--include-flagged", action="store_true", help="Also apply off-air, closed or input-less candidates")

    command("records", cmd_records, "List applied records with their RepeaterBook source")
    command("unblock", cmd_unblock, "Clear an authentication block once its cause is corrected", json_flag=False)
    command("purge", cmd_purge, "Apply the 7/30/90-day retention rules now")
    p_delete = command("delete-all", cmd_delete_all, "Delete All RepeaterBook Data")
    p_delete.add_argument("--yes", action="store_true", help="Confirm")
