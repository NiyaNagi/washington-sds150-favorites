"""One place that turns a source name plus the local configuration into a
runnable adapter.

The CLI and the web UI each carried their own copy of this construction, and
the fleet update wizard is a third caller, so it lives here and every entry
point delegates. Adapters that need local configuration (a Sentinel
workspace, a RadioReference export) come back as ``None`` when nothing is
configured, which callers report as "not configured" rather than as a
failure.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Collection, List, Optional

from wasds150.config import AppConfig
from wasds150.sources.base import OnlineSourceAdapter
from wasds150.sources.config import SourcesConfig
from wasds150.sources.registry import get_source_class, list_sources


def build_http_client(config: AppConfig, offline: bool) -> Any:
    """The cached HTTP client every online adapter fetches through."""
    from wasds150.cache.http import CachedHttpClient
    from wasds150.cache.store import HttpCacheStore

    return CachedHttpClient(HttpCacheStore(config.cache_dir), offline=offline)


def _sentinel_local(sources_config: SourcesConfig) -> Optional[OnlineSourceAdapter]:
    from wasds150.sources.sentinel_local import SentinelLocalSource

    if sources_config.sentinel_local_mount:
        return SentinelLocalSource(mount_point=Path(sources_config.sentinel_local_mount))
    if sources_config.sentinel_local_hpdb_cfg:
        return SentinelLocalSource(hpdb_cfg_path=Path(sources_config.sentinel_local_hpdb_cfg))
    return None


def _radioreference_premium(sources_config: SourcesConfig) -> Optional[OnlineSourceAdapter]:
    from wasds150.sources.radioreference_premium import (
        RadioReferenceCredentials,
        RadioReferencePremiumSource,
    )

    if sources_config.radioreference_export_path:
        return RadioReferencePremiumSource(export_path=Path(sources_config.radioreference_export_path))
    if sources_config.radioreference_username and sources_config.radioreference_app_key:
        return RadioReferencePremiumSource(
            credentials=RadioReferenceCredentials(
                username=sources_config.radioreference_username,
                app_key=sources_config.radioreference_app_key,
            )
        )
    return None


def instantiate_source(name: str, sources_config: SourcesConfig) -> Optional[OnlineSourceAdapter]:
    """Build a ready-to-run adapter for ``sources fetch``/``update``.

    Returns ``None`` for a legacy/placeholder adapter, or for a local adapter
    with nothing configured to read (``sentinel_local`` with no path set).
    Raises :class:`KeyError` for a name the registry does not know.
    """
    cls = get_source_class(name)
    if not issubclass(cls, OnlineSourceAdapter):
        return None  # static_pack / legacy placeholders: not part of the update pipeline
    if name == "sentinel_local":
        return _sentinel_local(sources_config)
    if name == "radioreference_premium":
        return _radioreference_premium(sources_config)
    if name == "faa_nasr":
        from wasds150.sources.faa_nasr import DEFAULT_SUBJECTS, FaaNasrSource

        return FaaNasrSource(subjects=tuple(sources_config.faa_nasr_subjects or DEFAULT_SUBJECTS))
    if name == "fcc_uls":
        return _fcc_uls(sources_config)
    return cls()


def _fcc_uls(sources_config: SourcesConfig) -> OnlineSourceAdapter:
    from wasds150.sources.fcc_uls import FccUlsSource

    home = None
    if sources_config.fcc_uls_within_miles:
        from wasds150.plans.template import HOME

        home = HOME
    return FccUlsSource(
        services=tuple(sources_config.fcc_uls_services or ("lmpriv",)),
        emissions=tuple(sources_config.fcc_uls_emissions or ()),
        home=home,
        within_miles=sources_config.fcc_uls_within_miles or None,
        active_only=sources_config.fcc_uls_active_only,
    )


def runnable_source_names(
    *, only: Optional[Collection[str]] = None, skip: Collection[str] = ()
) -> List[str]:
    """Available online adapters in registry order, narrowed to ``only``
    (when given) and without ``skip``. Unknown names in either are ignored,
    matching how ``sources update --only`` has always behaved."""
    names = []
    for name, cls in list_sources().items():
        if not issubclass(cls, OnlineSourceAdapter) or not cls.available:
            continue
        if only is not None and name not in only:
            continue
        if name in skip:
            continue
        names.append(name)
    return names


def instantiate_all(
    sources_config: SourcesConfig,
    *,
    only: Optional[Collection[str]] = None,
    skip: Collection[str] = (),
) -> List[OnlineSourceAdapter]:
    """Every runnable adapter, skipping local ones with nothing configured."""
    instances = []
    for name in runnable_source_names(only=only, skip=skip):
        instance = instantiate_source(name, sources_config)
        if instance is not None:
            instances.append(instance)
    return instances
