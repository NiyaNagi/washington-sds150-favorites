"""USCG NAVCEN US marine VHF channel plan (national reference table).

**Confirmed live source**: ``https://www.navcen.uscg.gov/us-vhf-channel-information``
returns a static (non-JS) page with two ``<table>``s: the main channel plan
(new channel #, legacy channel #, ship-TX MHz, ship-RX MHz, use) and the
fixed NOAA Weather channel set (WX1-WX7). Confirmed via a direct fetch
during implementation (52-row main table incl. header, 8-row weather
table).

This is a **national reference table, not a per-state feed** — it changes
only on regulatory action (the 2024 four-digit channel renumbering per
USCG's MSIB 07-24 was the last such change), so it is treated as
effectively static and re-checked annually rather than polled frequently.

Public domain (US federal work) — fully ingestible/redistributable.
"""
from __future__ import annotations

import datetime
from typing import Any, List, Optional

from wasds150.sources.base import OnlineSourceAdapter, RawDoc
from wasds150.sources.facts import NormalizedFact, NormalizeResult
from wasds150.sources.htmlutil import extract_tables

VHF_CHANNEL_INFO_URL = "https://www.navcen.uscg.gov/us-vhf-channel-information"
#: Channel plan changes only on regulatory action; check annually.
DEFAULT_TTL_SECONDS = 365 * 24 * 3600


class UscgNavcenSource(OnlineSourceAdapter):
    name = "uscg_navcen"
    available = True
    kind = "facts"

    def __init__(self, url: str = VHF_CHANNEL_INFO_URL, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self.url = url
        self.ttl_seconds = ttl_seconds

    def fetch(self, http_client: Optional[Any] = None) -> RawDoc:
        if http_client is None:
            raise ValueError(f"{self.name} requires an http_client")
        result = http_client.fetch(self.url, ttl_seconds=self.ttl_seconds, source_id=self.name)
        return RawDoc(
            source_adapter=self.name,
            payload=result.content.decode("utf-8"),
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        )

    def normalize(self, raw: RawDoc) -> NormalizeResult:
        tables = extract_tables(raw.payload)
        facts: List[NormalizedFact] = []
        warnings: List[str] = []

        if len(tables) >= 1:
            main_table = tables[0]
            header, rows = main_table[0], main_table[1:]
            expected_header = ["New Channel Number", "Old Channel Number", "Ship Transmit MHz", "Ship Receive MHz", "Use"]
            if header != expected_header:
                warnings.append(f"unexpected main table header: {header!r}")
            for row in rows:
                if len(row) < 5:
                    continue
                new_ch, old_ch, tx_mhz, rx_mhz, use = row[0], row[1], row[2], row[3], row[4]
                try:
                    freq = float(tx_mhz)
                except ValueError:
                    warnings.append(f"channel {new_ch}: could not parse frequency {tx_mhz!r}")
                    continue
                facts.append(
                    NormalizedFact(
                        entity_key=f"uscg_vhf:{new_ch}",
                        fact_type="channel_plan",
                        name=f"Marine VHF Ch {new_ch} ({old_ch})" if old_ch != new_ch else f"Marine VHF Ch {new_ch}",
                        freq_mhz=freq,
                        mode="FM",
                        location_precision="unknown",
                        source_id=self.name,
                        source_url=self.url,
                        retrieved_at=raw.fetched_at,
                        raw={"new_channel": new_ch, "old_channel": old_ch, "rx_mhz": rx_mhz, "use": use},
                    )
                )
        else:
            warnings.append("no tables found on USCG VHF channel information page")

        if len(tables) >= 2:
            wx_table = tables[1]
            for row in wx_table[1:]:
                if len(row) < 2:
                    continue
                channel, freq_s = row[0], row[1]
                try:
                    freq = float(freq_s)
                except ValueError:
                    continue
                facts.append(
                    NormalizedFact(
                        entity_key=f"uscg_vhf:{channel}",
                        fact_type="channel_plan",
                        name=f"NOAA Weather {channel}",
                        freq_mhz=freq,
                        mode="FM",
                        location_precision="unknown",
                        source_id=self.name,
                        source_url=self.url,
                        retrieved_at=raw.fetched_at,
                        raw={"channel": channel},
                    )
                )

        return NormalizeResult(facts=facts, warnings=warnings)
