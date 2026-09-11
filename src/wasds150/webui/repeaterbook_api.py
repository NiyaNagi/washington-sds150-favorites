"""Web UI routes for RepeaterBook, kept out of :mod:`wasds150.webui.api`.

Every handler goes through
:class:`wasds150.sources.repeaterbook.service.RepeaterBookService`, the same
guards the CLI uses. The browser never sees or sends a token: configuration
takes only an environment-variable *name* or an external file *path*, and
every response that carries RepeaterBook-derived records also carries the
attribution the UI must show.
"""
from __future__ import annotations

from typing import Any, Callable

from wasds150.webui.router import RequestContext, Response, Router


def _error(status: int, message: str) -> Response:
    return Response.json(status, {"error": message})


def _service(ctx):
    from wasds150.sources.repeaterbook.service import RepeaterBookService

    return RepeaterBookService(ctx.config)


def _guarded(action: Callable[[], Any]) -> Response:
    """Map a refusal or failure to a status code; the message is already
    redacted by the exception itself."""
    from wasds150.sources.repeaterbook.client import RepeaterBookError
    from wasds150.sources.repeaterbook.normalize import ResponseShapeError
    from wasds150.sources.repeaterbook.service import LimitError, NotEnabledError, PolicyError
    from wasds150.sources.repeaterbook.store import ActionInProgress
    from wasds150.sources.repeaterbook.token import TokenError

    try:
        return Response.json(200, action())
    except NotEnabledError as exc:
        return _error(403, str(exc))
    except (LimitError, ActionInProgress) as exc:
        return _error(409, str(exc))
    except (PolicyError, TokenError) as exc:
        return _error(400, str(exc))
    except (RepeaterBookError, ResponseShapeError) as exc:
        return _error(502, str(exc))


def _list(value: Any):
    if isinstance(value, str):
        return tuple(part.strip() for part in value.split(",") if part.strip())
    return tuple(value or ())


def get_status(ctx, req: RequestContext) -> Response:
    return _guarded(lambda: _service(ctx).status())


def get_regions(ctx, req: RequestContext) -> Response:
    from wasds150.sources.repeaterbook.policy import REGIONS

    return Response.json(
        200,
        {"regions": [
            {"code": r.code, "name": r.name, "country": r.country, "verified": r.verified, "note": r.note}
            for r in REGIONS.values()
        ]},
    )


def post_configure(ctx, req: RequestContext) -> Response:
    body = req.json_body() or {}
    if "token" in body:
        return _error(400, "the token itself is never accepted here; give an environment-variable name or a file path")
    return _guarded(
        lambda: _service(ctx).configure(
            enabled=body["enabled"] if "enabled" in body else None,
            token_env=body.get("token_env"),
            token_file=body.get("token_file"),
        )
    )


def post_forget_token(ctx, req: RequestContext) -> Response:
    return _guarded(lambda: _service(ctx).forget_token())


def post_refresh(ctx, req: RequestContext) -> Response:
    from wasds150.sources.repeaterbook.service import PolicyError, RefreshRequest, parse_center

    body = req.json_body() or {}

    def action():
        center = body.get("center")
        if isinstance(center, str):
            center = parse_center(center)
        if not isinstance(center, (list, tuple)) or len(center) != 2:
            raise PolicyError("exactly one centre [latitude, longitude] is required")
        request = RefreshRequest(
            regions=_list(body.get("regions")),
            center=(center[0], center[1]),
            radius_mi=body.get("radius_mi"),
            bands=_list(body.get("bands")),
            radio_id=str(body.get("radio") or ""),
        )
        return _service(ctx).refresh(request, offline=bool(body.get("offline")))

    return _guarded(action)


def get_staged(ctx, req: RequestContext) -> Response:
    action_id = (req.query.get("action") or [None])[0]
    return _guarded(lambda: _service(ctx).staged(action_id))


def post_apply(ctx, req: RequestContext) -> Response:
    body = req.json_body() or {}
    return _guarded(
        lambda: _service(ctx).apply(body.get("action_id"), include_flagged=bool(body.get("include_flagged")))
    )


def get_records(ctx, req: RequestContext) -> Response:
    return _guarded(lambda: _service(ctx).records())


def post_unblock(ctx, req: RequestContext) -> Response:
    return _guarded(lambda: {"cleared": _service(ctx).unblock_auth()})


def post_purge(ctx, req: RequestContext) -> Response:
    return _guarded(lambda: {"purged": _service(ctx).purge()})


def post_delete_all(ctx, req: RequestContext) -> Response:
    body = req.json_body() or {}
    if body.get("confirm") != "DELETE":
        return _error(400, "Delete All RepeaterBook Data needs {\"confirm\": \"DELETE\"}")
    return _guarded(lambda: {"deleted": _service(ctx).delete_all()})


def register(router: Router, ctx) -> None:
    base = "/api/v1/repeaterbook"
    router.add("GET", f"{base}/status", lambda req: get_status(ctx, req))
    router.add("GET", f"{base}/regions", lambda req: get_regions(ctx, req))
    router.add("POST", f"{base}/configure", lambda req: post_configure(ctx, req))
    router.add("POST", f"{base}/forget-token", lambda req: post_forget_token(ctx, req))
    router.add("POST", f"{base}/refresh", lambda req: post_refresh(ctx, req))
    router.add("GET", f"{base}/staged", lambda req: get_staged(ctx, req))
    router.add("POST", f"{base}/apply", lambda req: post_apply(ctx, req))
    router.add("GET", f"{base}/records", lambda req: get_records(ctx, req))
    router.add("POST", f"{base}/unblock", lambda req: post_unblock(ctx, req))
    router.add("POST", f"{base}/purge", lambda req: post_purge(ctx, req))
    router.add("POST", f"{base}/delete-all", lambda req: post_delete_all(ctx, req))
