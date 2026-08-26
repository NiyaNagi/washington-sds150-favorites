"""Operator-programmed TH-D75 channels recovered from the current radio image.

These are intentionally separate from public repeater sources. They reproduce
what the operator entered, including non-standard 600 kHz UHF offsets, without
claiming that the assignments have been independently coordinated or verified.
"""
from __future__ import annotations

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

SOURCE_SHA256 = "25E7330FA52E7AE50E4CE5C0406E41955C06FC0C3A7639C29968B6AF1B85116A"


def _channel(label: str, rx: float, tx: float, notes: str) -> Channel:
    return Channel(
        id=stable_id(f"thd75-user:{label}:{rx}:{tx}", kind="channel"),
        label=label,
        freq_mhz=rx,
        tx_freq_mhz=tx,
        mode="FM",
        tone="TONE=C103.5",
        service_type=13,
        notes=notes,
    )


def favorite() -> FavoritesList:
    channels = [
        _channel(
            "VAERPT",
            443.050,
            443.650,
            "Recovered from operator memory 538: +0.600 MHz, transmit CTCSS 103.5 Hz; independently unverified.",
        ),
        _channel(
            "N7QT Redmond",
            442.325,
            442.925,
            "Recovered from operator memory 539: FM, +0.600 MHz, transmit CTCSS 103.5 Hz. This conflicts with the current WWARA record describing N7QT on this output as DMR with a +5 MHz input; retained exactly as operator-programmed.",
        ),
        _channel(
            "W7AUX",
            442.825,
            442.825,
            "Recovered from operator memory 540: FM simplex with transmit CTCSS 103.5 Hz. Current public coordination data list W7AUX on this output as P25; retained exactly as operator-programmed.",
        ),
    ]
    return FavoritesList(
        id=stable_id("thd75-user:current", kind="favorites-list"),
        slug="thd75user",
        favorite_key="THD75USER",
        favorite_name="TH-D75 Operator-Programmed Channels",
        region="Ames Lake / Redmond operating area",
        counties="King",
        scenario="Operator-entered memories preserved from the radio",
        source_type="Current MCP-D75 radio image",
        system_or_category="Operator additions",
        sites_or_coverage="Not independently verified",
        departments_or_channels="VAERPT; N7QT Redmond; W7AUX",
        mode="FM",
        monitorability="Native on TH-D75",
        upgrade_required="None",
        source_url="",
        notes=f"Recovered 2026-08-26 from TH-D75 configuration SHA-256 {SOURCE_SHA256}.",
        systems=[
            System(
                id=stable_id("thd75-user:system", kind="system"),
                label="TH-D75 Operator Additions",
                departments=[
                    Department(
                        id=stable_id("thd75-user:channels", kind="department"),
                        label="Operator-Programmed Channels",
                        channels=channels,
                    )
                ],
            )
        ],
        provenance=[
            Provenance(
                source_adapter="operator_radio_image",
                confidence="derived",
            )
        ],
    )
