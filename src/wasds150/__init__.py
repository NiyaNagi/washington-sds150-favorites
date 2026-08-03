"""wasds150: generate Uniden SDS150 Favorites Lists from the Washington catalog.

This package is intentionally split so later research phases (HPE binary
codec, RadioReference/other online source adapters, three-way merge with
upstream sources, SD-card installer) can be dropped in without touching the
phases implemented here: canonical models, baseline catalog, profile
editing, deterministic generation, snapshot history, CLI, and a local
browser UI.
"""

__version__ = "0.1.0"
