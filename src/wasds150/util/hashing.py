"""Deterministic hashing helpers.

Everything that needs a stable identity or change-detection hash in
wasds150 (catalog entries, generated bundles, snapshots) goes through
``canonical_json`` + ``sha256_of`` so that hashing never depends on Python
dict ordering, locale, or wall-clock time.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

# Fixed namespace UUID for deriving stable ids from slugs. This value is
# arbitrary but MUST NOT change, or every previously generated id will
# change too.
ID_NAMESPACE = uuid.UUID("6c1b1c2e-8f2a-4e2a-9b0a-3a5e9d7f2b10")


def canonical_json(obj: Any) -> str:
    """Serialize ``obj`` deterministically: sorted keys, stable separators.

    Only JSON-native types (dict/list/str/int/float/bool/None) are
    supported; callers are responsible for converting dataclasses first.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_of_bytes(data: bytes) -> str:
    """Binary-safe sibling of :func:`sha256_of`, for hashing file content
    that is not (necessarily) valid UTF-8 text — e.g. a generated ``.hpe``
    file, which is XOR/gzip binary, not text (see
    :mod:`wasds150.bundle.manifest`)."""
    return hashlib.sha256(data).hexdigest()


def content_hash(obj: Any) -> str:
    """sha256 over the canonical JSON form of ``obj``."""
    return sha256_of(canonical_json(obj))


def stable_id(slug: str, kind: str = "favorites_list") -> str:
    """Deterministic uuid5 id derived from a stable slug + entity kind."""
    return str(uuid.uuid5(ID_NAMESPACE, f"{kind}:{slug}"))
