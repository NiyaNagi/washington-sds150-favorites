"""Download the contact directories the fleet's radios can hold."""
from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

from wasds150.appctx import AppContext
from wasds150.contacts.model import ContactStore
from wasds150.contacts.radioid import RadioIdSource


def protocols_for_fleet() -> Tuple[str, ...]:
    """Every protocol some registered radio keeps a contact list for."""
    from wasds150.radios.registry import list_profiles

    wanted = set()
    for profile in list_profiles().values():
        if profile.contacts is not None:
            wanted |= set(profile.contacts.protocols)
    return tuple(sorted(wanted))


def refresh_contacts(
    ctx: AppContext,
    job: Any = None,
    *,
    http_client: Optional[Any] = None,
    protocols: Optional[Sequence[str]] = None,
) -> str:
    """Fetch radioid.net and store each table; returns a one-line summary.

    radioid.net republishes its directories every day, so every refresh
    revalidates with the server rather than trusting the cached copy's
    30-day TTL. The request is conditional: an unchanged directory costs one
    round trip, a changed one is downloaded."""
    wanted = tuple(protocols or protocols_for_fleet())
    if not wanted:
        return "no radio keeps a contact list"
    if http_client is None:
        from wasds150.sources.config import SourcesConfig
        from wasds150.sources.factory import build_http_client

        http_client = build_http_client(ctx.config, SourcesConfig.load(ctx.config.sources_config_path).offline)
    source = RadioIdSource(protocols=wanted)
    raw = source.fetch(http_client, force=True)
    store = ContactStore(ctx.config.contacts_dir)
    parts = []
    for table in source.tables(raw):
        store.save(table)
        parts.append(f"{table.protocol} {len(table.rows):,} contacts")
        if job is not None:
            job.log(f"{table.protocol}: {len(table.rows):,} contacts from {table.source_url}")
    return "; ".join(parts)
