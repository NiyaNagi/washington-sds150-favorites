"""Registry of known source adapters (by name), for the CLI/UI to list.

Two adapter families are registered side by side (see
:mod:`wasds150.sources.base` for why): legacy :class:`SourceAdapter`
(``static_pack``, plus the still-unimplemented ``radioreference_free`` and
``repeaterbook`` placeholders — public-page scraping/bulk-mirroring that
stays intentionally out of scope, see ``docs/data-sources.md``), and the
newer fact-producing :class:`OnlineSourceAdapter` family (everything else
below), each independently verified against real data or file formats
during implementation (see each adapter's module docstring for specifics).

``available=False`` entries are still listed (never hidden) so the CLI/UI
can show users what exists but isn't wired up, instead of silently
omitting it.
"""
from __future__ import annotations

from typing import Dict, Type, Union

from wasds150.sources.amsat import AmsatSource
from wasds150.sources.base import OnlineSourceAdapter, SourceAdapter
from wasds150.sources.faa_nasr import FaaNasrSource
from wasds150.sources.fcc_uls import FccUlsSource
from wasds150.sources.iacc import IaccSource
from wasds150.sources.nifc import NifcSource
from wasds150.sources.noaa_wx import NoaaNwrSource
from wasds150.sources.nwac import NwacSource
from wasds150.sources.radioreference_free import RadioReferenceFreeSource
from wasds150.sources.radioreference_premium import RadioReferencePremiumSource
from wasds150.sources.repeaterbook import RepeaterBookSource
from wasds150.sources.sentinel_local import SentinelLocalSource
from wasds150.sources.static_pack import StaticPackSource
from wasds150.sources.uscg_navcen import UscgNavcenSource
from wasds150.sources.wa_dnr import WaDnrSource
from wasds150.sources.wa_emd import WaEmdSource
from wasds150.sources.wwara import WwaraSource

AnySourceClass = Union[Type[SourceAdapter], Type[OnlineSourceAdapter]]

_REGISTRY: Dict[str, AnySourceClass] = {
    # Legacy local/placeholder adapters.
    StaticPackSource.name: StaticPackSource,
    RadioReferenceFreeSource.name: RadioReferenceFreeSource,
    RepeaterBookSource.name: RepeaterBookSource,
    # User-local (no network).
    SentinelLocalSource.name: SentinelLocalSource,
    RadioReferencePremiumSource.name: RadioReferencePremiumSource,
    # Online fact sources.
    NoaaNwrSource.name: NoaaNwrSource,
    UscgNavcenSource.name: UscgNavcenSource,
    AmsatSource.name: AmsatSource,
    WwaraSource.name: WwaraSource,
    IaccSource.name: IaccSource,
    FaaNasrSource.name: FaaNasrSource,
    FccUlsSource.name: FccUlsSource,
    # Online change-detection-only sources (PDF/image landing pages).
    NwacSource.name: NwacSource,
    WaEmdSource.name: WaEmdSource,
    WaDnrSource.name: WaDnrSource,
    NifcSource.name: NifcSource,
}


def list_sources() -> Dict[str, AnySourceClass]:
    return dict(_REGISTRY)


def get_source_class(name: str) -> AnySourceClass:
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(f"Unknown source {name!r}; known sources: {sorted(_REGISTRY)}") from None
