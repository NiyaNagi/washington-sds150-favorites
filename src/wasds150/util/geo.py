"""Geographic distance, shared by the scanner and the channel planner.

Both need the same answer to "how far apart are these two points", so the
calculation lives here rather than being written twice with two different
Earth radii and drifting apart.
"""
from __future__ import annotations

import math

#: Statute miles. Chosen to match Uniden's mile-based ``range`` field, so a
#: geo-fence this project computes agrees with one the scanner enforces.
EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points, in statute miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * EARTH_RADIUS_MILES * math.asin(min(1.0, math.sqrt(a)))
