"""Every number and identifier the RepeaterBook adapter is allowed to use.

One module, so the whole policy can be reviewed on one screen and a stricter
value RepeaterBook approves is a one-line change. See
``docs/repeaterbook-api-compliance-design.md`` for why each value is what it
is; the endpoint, parameter names, header and token rules come from
RepeaterBook's API documentation at :data:`API_DOCS_URL`.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

#: RepeaterBook's API documentation, the source of every identifier below.
API_DOCS_URL = "https://www.repeaterbook.com/wiki/doku.php?id=api"

#: Sent byte-for-byte on every request; the client refuses to send anything
#: else. Carries the public project URL and a reachable contact, as the
#: documentation's User-Agent requirements ask.
USER_AGENT = "SignalWA/1.0 (+https://github.com/NiyaNagi/washington-sds150-favorites; ajamess@gmail.com)"

#: The North America export endpoint (token scope ``api.export``). The
#: documentation's example ``export.php?country=United%20States&country=Canada``
#: shows it also serves Canada, so the rest-of-world endpoint
#: (``exportROW.php``, scope ``api.export_row``) is never used.
EXPORT_ENDPOINT = "https://www.repeaterbook.com/api/export.php"
REQUIRED_SCOPE = "api.export"

#: The documentation's preferred header for an app-bound user token.
TOKEN_HEADER = "X-RB-App-Token"
#: A distributed application's per-user, app-bound token.
TOKEN_PREFIX = "rbuapp_"
#: A shared application token. Never accepted: this is a distributed app.
SHARED_TOKEN_PREFIX = "app_"
DEFAULT_TOKEN_ENV = "REPEATERBOOK_API_TOKEN"

# -- request bounds -----------------------------------------------------------
RADIUS_MIN_MI = 1
RADIUS_MAX_MI = 60
RADIUS_DEFAULT_MI = 60
#: More candidates than this after local filtering imports nothing.
CANDIDATE_CAP = 250
#: Regions one user action may request, one HTTP request each, in sequence.
MAX_REGIONS_PER_ACTION = 3
#: HTTP requests per token in any rolling 24 hours.
MAX_REQUESTS_PER_24H = 4
REQUEST_WINDOW = datetime.timedelta(hours=24)
#: The same region is not requested again sooner than this.
REGION_COOLDOWN = datetime.timedelta(minutes=60)
#: A 429 locks refresh for at least this long, or for Retry-After if longer.
RATE_LIMIT_LOCKOUT = datetime.timedelta(minutes=60)
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 10 * 1024 * 1024

# -- retention ------------------------------------------------------------------
#: Raw responses may be newly applied only while this fresh.
RAW_FRESH = datetime.timedelta(days=7)
#: Raw responses and staging rows are deleted by this age.
RAW_DELETE_AFTER = datetime.timedelta(days=30)
STAGING_DELETE_AFTER = datetime.timedelta(days=30)
#: Applied (derived) records are deleted by this age unless reviewed again.
DERIVED_DELETE_AFTER = datetime.timedelta(days=90)
#: The request ledger (history, not the rate-limit window) is kept this long.
LEDGER_DELETE_AFTER = datetime.timedelta(days=30)

# -- attribution ------------------------------------------------------------------
ATTRIBUTION_TEXT = "Data courtesy of RepeaterBook.com"
ATTRIBUTION_URL = "https://www.repeaterbook.com/"
#: A per-record detail page. The documentation asks for one "when
#: practical" but does not state its form, so until RepeaterBook confirms it
#: records link to :data:`ATTRIBUTION_URL` and show their RepeaterBook id.
DETAIL_URL_TEMPLATE = "https://www.repeaterbook.com/repeaters/details.php?state_id={state_id}&ID={rb_id}"
DETAIL_URL_CONFIRMED = False

PENDING_APPROVAL_MESSAGE = (
    "RepeaterBook access is off. The adapter is pending RepeaterBook approval; "
    "enable it with 'wasds150 repeaterbook configure --enable' only once "
    "RepeaterBook has approved this application and you hold your own rbuapp_ token."
)

#: Amateur bands a refresh may select (MHz, inclusive).
AMATEUR_BANDS: Dict[str, Tuple[float, float]] = {
    "6m": (50.0, 54.0),
    "2m": (144.0, 148.0),
    "1.25m": (222.0, 225.0),
    "70cm": (420.0, 450.0),
    "33cm": (902.0, 928.0),
    "23cm": (1240.0, 1300.0),
}


@dataclass(frozen=True)
class Region:
    """One allowlisted export region. ``verified`` is False when a parameter
    could not be confirmed from RepeaterBook's documentation; such a region is
    listed but refused."""

    code: str
    name: str
    country: str
    state_id: Optional[str]
    verified: bool
    note: str

    def query(self) -> Tuple[Tuple[str, str], ...]:
        """The request's query parameters, in a fixed order. Nothing else is
        ever sent: no pagination, no wildcard, no search term."""
        if not self.verified or not self.state_id:
            raise ValueError(f"region {self.code} is not enabled: {self.note}")
        return (("country", self.country), ("state_id", self.state_id))


_FIPS = "US Census FIPS state code; RepeaterBook documents state_id as the FIPS code"

#: The allowlist. A region absent here cannot be requested at all.
REGIONS: Dict[str, Region] = {
    "WA": Region("WA", "Washington", "United States", "53", True, _FIPS),
    "OR": Region("OR", "Oregon", "United States", "41", True, _FIPS),
    "ID": Region("ID", "Idaho", "United States", "16", True, _FIPS),
    "BC": Region(
        "BC",
        "British Columbia",
        "Canada",
        None,
        False,
        "export.php serves Canada, but the documentation does not give the "
        "state_id RepeaterBook uses for a province; disabled until RepeaterBook "
        "confirms it",
    ),
}
