"""RepeaterBook Export API adapter: implemented, off by default, explicit-only.

Nothing here runs unless the operator has (1) turned on the local enable flag,
which stays off pending RepeaterBook's approval of this application, (2)
supplied their own app-bound ``rbuapp_`` token, and (3) started a refresh by
hand. ``sources update`` and ``sources fetch`` never run it; normal radio
export never calls it.

Modules:

* :mod:`.policy` -- every limit, identifier and the region allowlist
* :mod:`.token` -- token loading, prefix rules, fingerprinting, redaction
* :mod:`.client` -- the one place a request is sent
* :mod:`.store` -- a dedicated local store with retention and Delete All
* :mod:`.normalize` -- response parsing and local filtering
* :mod:`.service` -- refresh -> review -> apply, and status
* :mod:`.catalog` -- reviewed records as a local-only Favorites List

See ``docs/repeaterbook-api-compliance-design.md``.
"""
from __future__ import annotations

from typing import Any, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizeResult

EXPLICIT_ONLY_MESSAGE = (
    "RepeaterBook is never fetched by 'sources fetch' or 'sources update'. Use "
    "'wasds150 repeaterbook refresh' (or the RepeaterBook panel), which carries the "
    "approval, token, region and rate-limit guards."
)


class ExplicitOnlyError(RuntimeError):
    """Raised when RepeaterBook is reached through the generic source paths."""


class RepeaterBookSource(OnlineSourceAdapter):
    """Listed with the other sources so it is visible, but never run by them."""

    name = "repeaterbook"
    available = True
    kind = "facts"
    explicit_only = True

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        raise ExplicitOnlyError(EXPLICIT_ONLY_MESSAGE)

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        raise ExplicitOnlyError(EXPLICIT_ONLY_MESSAGE)
