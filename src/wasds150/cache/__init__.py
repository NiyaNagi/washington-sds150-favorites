"""Content-addressed HTTP cache with TTL/conditional-GET, offline mode,
rate limiting, and provenance — the shared foundation every online source
adapter in :mod:`wasds150.sources` builds on.

See :mod:`wasds150.cache.store` (the sqlite-backed metadata index + blob
store) and :mod:`wasds150.cache.http` (the conditional-GET client with size
limits, rate limiting, and offline mode).
"""
