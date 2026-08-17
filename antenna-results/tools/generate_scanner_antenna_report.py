#!/usr/bin/env python3
"""Generate the SDS150 handheld scanner-antenna comparison package.

The script reads the calibrated Touchstone captures under
``antenna-results/antennas/`` and rebuilds every derived artifact:
per-family READMEs and charts, the cross-antenna comparison README,
the machine-readable scorecard (CSV + JSON), comparison charts, and the
self-contained offline interactive report.

Only measured files are read; nothing here is hand-tuned. Running the
script twice on unchanged inputs produces byte-identical output.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib
import numpy as np

matplotlib.use("Agg")

from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

REFERENCE_OHMS = 50.0
SCHEMA_ID = "sds150-scanner-antenna-scorecard/1.0"
VERY_POOR = "very poor / outside calibrated dynamic range"
HEATMAP_VMIN = 1.0
HEATMAP_VMAX = 6.0
CURVE_POINTS = 181

FIGURE_DPI = 130
PLOT_STYLE = {
    "figure.facecolor": "#ffffff",
    "axes.facecolor": "#ffffff",
    "axes.edgecolor": "#919191",
    "axes.labelcolor": "#242424",
    "axes.titlecolor": "#242424",
    "text.color": "#242424",
    "xtick.color": "#5c5c5c",
    "ytick.color": "#5c5c5c",
    "grid.color": "#dedede",
    "font.size": 10.0,
    "savefig.facecolor": "#ffffff",
}
SERIES_COLORS = (
    "#b11f4b",
    "#315c8c",
    "#23856d",
    "#b26a22",
    "#6d4c91",
    "#22758c",
    "#9a5433",
    "#4f6d3a",
    "#8c2f39",
    "#3f5d7d",
)


@dataclass(frozen=True)
class Service:
    """A receive service window the SDS150 is actually used on."""

    key: str
    label: str
    start_hz: int
    stop_hz: int
    group: str
    note: str

    @property
    def start_mhz(self) -> float:
        return self.start_hz / 1e6

    @property
    def stop_mhz(self) -> float:
        return self.stop_hz / 1e6

    @property
    def range_label(self) -> str:
        return "{0:g}-{1:g} MHz".format(self.start_mhz, self.stop_mhz)


@dataclass(frozen=True)
class Config:
    """One physically distinct antenna configuration."""

    key: str
    label: str
    directory: str
    note: str


@dataclass(frozen=True)
class Family:
    """An antenna model, optionally with several telescopic settings."""

    key: str
    label: str
    short_label: str
    kind: str
    connection: str
    valid: bool
    configs: Tuple[Config, ...]
    overview: str
    cautions: Tuple[str, ...] = ()
    invalid_reason: str = ""


SERVICES: Tuple[Service, ...] = (
    Service("6m", "6m amateur", 50_000_000, 54_000_000, "VHF low",
            "Amateur 6m; lowest frequency the broadband sweep covers."),
    Service("fm-broadcast", "FM broadcast", 88_000_000, 108_000_000, "VHF low",
            "Wideband FM broadcast listening."),
    Service("civil-air", "Civil air", 118_000_000, 137_000_000, "VHF air",
            "AM civil aviation voice."),
    Service("2m", "2m amateur", 144_000_000, 148_000_000, "VHF high",
            "Amateur 2m repeater and simplex."),
    Service("vhf-lmr", "VHF LMR", 150_000_000, 174_000_000, "VHF high",
            "VHF land mobile, including public safety and business."),
    Service("marine-vhf", "Marine VHF", 156_000_000, 162_000_000, "VHF high",
            "Marine channels including Coast Guard and bridge-to-bridge."),
    Service("railroad", "Railroad", 159_810_000, 161_565_000, "VHF high",
            "AAR railroad channels."),
    Service("noaa-weather", "NOAA weather", 162_400_000, 162_550_000, "VHF high",
            "NOAA Weather Radio All Hazards."),
    Service("1.25m", "1.25m amateur", 222_000_000, 225_000_000, "220 MHz",
            "Amateur 1.25m repeater and simplex."),
    Service("military-air", "Military air", 225_000_000, 400_000_000, "UHF air",
            "Wide AM military aviation range; no antenna tested covers it evenly."),
    Service("federal-uhf", "Federal UHF", 406_100_000, 420_000_000, "UHF",
            "Federal land mobile allocations."),
    Service("70cm", "70cm amateur", 420_000_000, 450_000_000, "UHF",
            "Amateur 70cm repeater and simplex."),
    Service("uhf-lmr", "UHF LMR", 450_000_000, 470_000_000, "UHF",
            "UHF land mobile, including public safety and business."),
    Service("t-band", "T-band", 470_000_000, 512_000_000, "UHF",
            "T-band public-safety and business systems."),
    Service("700-public-safety-downlink", "700 MHz public safety", 769_000_000, 775_000_000,
            "700/800/900", "P25 700 MHz public-safety downlink (what a scanner listens to)."),
    Service("800-public-safety-downlink", "800 MHz public safety", 851_000_000, 869_000_000,
            "700/800/900", "P25 and analog 800 MHz public-safety downlink."),
    Service("33cm", "33cm amateur", 902_000_000, 928_000_000, "700/800/900",
            "Amateur 33cm and shared ISM."),
    Service("900-trunking-downlink", "900 MHz trunking", 935_000_000, 941_000_000,
            "700/800/900", "900 MHz business/SMR trunking downlink."),
    Service("uat-978", "UAT 978", 976_000_000, 980_000_000, "L-band",
            "978 MHz Universal Access Transceiver (ADS-B UAT)."),
    Service("ads-b-1090", "ADS-B 1090", 1_088_000_000, 1_092_000_000, "L-band",
            "1090 MHz ADS-B / Mode S."),
)

SERVICE_BY_KEY: Dict[str, Service] = {service.key: service for service in SERVICES}

FAMILIES: Tuple[Family, ...] = (
    Family(
        key="remtronix-920",
        label="Remtronix 920",
        short_label="Remtronix 920",
        kind="fixed",
        connection="BNC, direct to the measurement plane",
        valid=True,
        configs=(
            Config(
                key="remtronix-920",
                label="BNC direct",
                directory="remtronix-920/measurements/2026-08-16-bnc-plane",
                note="Single fixed configuration; no adjustment available.",
            ),
        ),
        overview=(
            "A short fixed whip aimed at the 700/800/900 MHz public-safety and "
            "trunking downlinks. It is the only antenna measured here that holds a "
            "good match across every modern trunked public-safety window, and it is "
            "also the best of the tested set at 33cm, 900 MHz trunking, and the "
            "L-band aviation data frequencies."
        ),
        cautions=(
            "It is deliberately narrow-band: VHF, civil air, 2m, and the 220 MHz "
            "band are all far outside its match.",
            "A good match at 978 and 1090 MHz is still only moderate, and impedance "
            "match is not the same thing as gain.",
        ),
    ),
    Family(
        key="rh789",
        label="RH789 telescopic",
        short_label="RH789",
        kind="telescopic",
        connection="BNC, direct to the measurement plane",
        valid=True,
        configs=(
            Config("rh789:setting-1", "setting 1", "rh789/measurements/setting-1-collapsed",
                   "Fully collapsed."),
            Config("rh789:setting-2", "setting 2", "rh789/measurements/setting-2",
                   "Fixed vane 1 plus vane 2 fully extended."),
            Config("rh789:setting-3", "setting 3", "rh789/measurements/setting-3",
                   "Fixed vane 1 plus vanes 2-3 fully extended."),
            Config("rh789:setting-4", "setting 4", "rh789/measurements/setting-4",
                   "Fixed vane 1 plus vanes 2-4 fully extended."),
            Config("rh789:setting-5", "setting 5", "rh789/measurements/setting-5",
                   "Fixed vane 1 plus vanes 2-5 fully extended."),
            Config("rh789:setting-6", "setting 6", "rh789/measurements/setting-6-fully-extended",
                   "Fixed vane 1 plus vanes 2-6 fully extended (maximum length)."),
        ),
        overview=(
            "A telescopic whip whose match moves predictably with length, so one "
            "antenna can be retuned by hand for VHF land mobile, federal UHF, UHF "
            "land mobile, and the T-band. It is the widest-coverage antenna tested, "
            "but only if the operator is willing to change the setting."
        ),
        cautions=(
            "Every useful result depends on the setting; the wrong length is much "
            "worse than a fixed antenna.",
            "It is weak across 700/800/900 MHz, which is where most modern "
            "public-safety traffic lives.",
        ),
    ),
    Family(
        key="tid-td771",
        label="TID TD771",
        short_label="TID TD771",
        kind="fixed",
        connection="SMA antenna with an SMA-to-BNC adapter",
        valid=True,
        configs=(
            Config(
                key="tid-td771",
                label="with SMA-to-BNC adapter",
                directory="tid-td771/measurements/2026-08-16-with-sma-bnc-adapter",
                note="Single fixed configuration measured through the required adapter.",
            ),
        ),
        overview=(
            "A long flexible whip that turned out to be the standout performer on "
            "the 222-225 MHz amateur band, where it holds a very good match across "
            "the entire allocation. Elsewhere it is narrow, with isolated responses "
            "near 225 MHz and 422 MHz."
        ),
        cautions=(
            "VHF land mobile and the 700/800 MHz public-safety windows are poor in "
            "this fixture.",
            "Results include the SMA-to-BNC adapter, which is part of the "
            "practical installation.",
        ),
    ),
    Family(
        key="diamond-srh77ca",
        label="Diamond SRH77CA",
        short_label="Diamond SRH77CA",
        kind="fixed",
        connection="SMA antenna with a BNC adapter",
        valid=True,
        configs=(
            Config(
                key="diamond-srh77ca",
                label="with BNC adapter",
                directory="diamond-srh77ca/measurements/2026-08-16-with-bnc-adapter",
                note="Single fixed configuration measured through the required adapter.",
            ),
        ),
        overview=(
            "A well-known dual-band flexible whip. In this fixture it is the "
            "strongest broad choice for 420-450 MHz and is a solid alternate for "
            "222-225 MHz, with a narrow military-air response near 227.5 MHz."
        ),
        cautions=(
            "The VHF half of its nominal dual-band design did not match well in "
            "this no-chassis fixture.",
            "700/800 MHz public safety is poor.",
        ),
    ),
    Family(
        key="generic-extendable",
        label="Generic extendable whip",
        short_label="Generic extendable",
        kind="telescopic",
        connection="BNC, direct to the measurement plane",
        valid=True,
        configs=(
            Config("generic-extendable:setting-1", "setting 1",
                   "generic-extendable/measurements/setting-1-collapsed", "Fully collapsed."),
            Config("generic-extendable:setting-2", "setting 2",
                   "generic-extendable/measurements/setting-2",
                   "Fixed vane 1 plus vane 2 fully extended."),
            Config("generic-extendable:setting-3", "setting 3",
                   "generic-extendable/measurements/setting-3",
                   "Fixed vane 1 plus vanes 2-3 fully extended."),
            Config("generic-extendable:setting-4", "setting 4",
                   "generic-extendable/measurements/setting-4",
                   "Fixed vane 1 plus vanes 2-4 fully extended."),
            Config("generic-extendable:setting-5", "setting 5",
                   "generic-extendable/measurements/setting-5",
                   "Fixed vane 1 plus vanes 2-5 fully extended."),
            Config("generic-extendable:setting-6", "setting 6",
                   "generic-extendable/measurements/setting-6",
                   "Fixed vane 1 plus vanes 2-6 fully extended."),
            Config("generic-extendable:setting-7", "setting 7",
                   "generic-extendable/measurements/setting-7",
                   "Fixed vane 1 plus vanes 2-7 fully extended."),
            Config("generic-extendable:setting-8", "setting 8",
                   "generic-extendable/measurements/setting-8",
                   "Fixed vane 1 plus vanes 2-8 fully extended."),
            Config("generic-extendable:setting-9", "setting 9",
                   "generic-extendable/measurements/setting-9",
                   "Fixed vane 1 plus vanes 2-9 fully extended."),
            Config("generic-extendable:setting-10", "setting 10",
                   "generic-extendable/measurements/setting-10-fully-extended",
                   "Fixed vane 1 plus vanes 2-10 fully extended (maximum length)."),
        ),
        overview=(
            "An unbranded telescopic whip captured at all ten settings. It is "
            "strongly geometry- and counterpoise-sensitive: later averaged zooms "
            "did not reproduce earlier broadband behaviour on the same setting, so "
            "this family is treated as experimental and session-specific."
        ),
        cautions=(
            "Setting 1 broadband and setting 1 averaged zoom disagree sharply. The "
            "authoritative zoom is poor (federal UHF minimum 3.34, 70cm minimum "
            "6.37), so the earlier broadband numbers should not be trusted.",
            "Do not choose this family over a stable fixed antenna or the RH789 on "
            "the strength of these numbers.",
        ),
    ),
    Family(
        key="uniden-sds150-stock",
        label="Uniden SDS150 stock rubber duck",
        short_label="SDS150 stock",
        kind="fixed",
        connection="stock scanner antenna with the required adapter",
        valid=True,
        configs=(
            Config(
                key="uniden-sds150-stock",
                label="stock with adapter",
                directory="uniden-sds150-stock/measurements/2026-08-16",
                note="The antenna shipped with the scanner, measured through the required adapter.",
            ),
        ),
        overview=(
            "The reference point: whatever the scanner already has on it. In this "
            "fixture it is usable around the 406-420 MHz federal band and near the "
            "bottom edge of 70cm, moderate on UHF land mobile, and poor everywhere "
            "else that was measured."
        ),
        cautions=(
            "A stock rubber duck is designed to work against the radio body. "
            "Measuring it on a bench fixture with no chassis understates VHF.",
            "Use it as the baseline the other antennas have to beat, not as a "
            "characterization of the shipped product.",
        ),
    ),
    Family(
        key="tidradio-h9-stock",
        label="TIDRADIO H9 stock antenna",
        short_label="TIDRADIO H9 stock",
        kind="fixed",
        connection="SMA antenna with adapter (as attempted)",
        valid=False,
        configs=(
            Config(
                key="tidradio-h9-stock",
                label="single broadband attempt",
                directory="tidradio-h9-stock/measurements/2026-08-16",
                note="Single broadband capture; invalid / inconclusive.",
            ),
        ),
        overview=(
            "One broadband capture was taken and immediately looked electrically "
            "open across the bands this antenna is designed for. Testing was "
            "stopped before any zoom or reseat verification."
        ),
        invalid_reason=(
            "The capture shows a near-total reflection across the antenna's own "
            "design bands: 2m, VHF land mobile, marine, railroad, NOAA weather, "
            "1.25m, UHF land mobile, and the T-band all read as an effectively "
            "infinite standing-wave ratio, which is the signature of an open or "
            "unseated connection rather than a working dual-band whip. The capture "
            "was never repeated after a reseat, so nothing here can be attributed "
            "to the antenna itself."
        ),
    ),
)

FAMILY_BY_KEY: Dict[str, Family] = {family.key: family for family in FAMILIES}
CONFIG_BY_KEY: Dict[str, Config] = {
    config.key: config for family in FAMILIES for config in family.configs
}
CONFIG_FAMILY: Dict[str, Family] = {
    config.key: family for family in FAMILIES for config in family.configs
}
VALID_FAMILIES: Tuple[Family, ...] = tuple(family for family in FAMILIES if family.valid)
VALID_CONFIG_KEYS: Tuple[str, ...] = tuple(
    config.key for family in VALID_FAMILIES for config in family.configs
)


@dataclass(frozen=True)
class Recommendation:
    """A practical 'use this here' mapping, written against measured data."""

    circumstance: str
    services: Tuple[str, ...]
    primary: Optional[str]
    alternates: Tuple[str, ...]
    guidance: str


RECOMMENDATIONS: Tuple[Recommendation, ...] = (
    Recommendation(
        "Modern 700 and 800 MHz public-safety trunking",
        ("700-public-safety-downlink", "800-public-safety-downlink"),
        "remtronix-920",
        (),
        "The only tested antenna that holds a good match across both downlink "
        "blocks. This is the normal SDS150 use case in Washington.",
    ),
    Recommendation(
        "900 MHz trunking, 33cm, and general 902-941 MHz listening",
        ("33cm", "900-trunking-downlink"),
        "remtronix-920",
        (),
        "Nothing else tested comes close in this range.",
    ),
    Recommendation(
        "VHF land mobile, marine, railroad, and NOAA weather (150-174 MHz)",
        ("vhf-lmr", "marine-vhf", "railroad", "noaa-weather"),
        "rh789:setting-5",
        (),
        "Extend the RH789 to setting 5. Usable rather than excellent, but it is "
        "the only tested configuration that works at all across 150-174 MHz.",
    ),
    Recommendation(
        "Federal UHF (406.1-420 MHz)",
        ("federal-uhf",),
        "rh789:setting-4",
        ("uniden-sds150-stock", "diamond-srh77ca"),
        "RH789 at setting 4 is the best broad match. The stock SDS150 antenna is a "
        "reasonable no-change alternate near the top of the band.",
    ),
    Recommendation(
        "UHF land mobile (450-470 MHz)",
        ("uhf-lmr",),
        "rh789:setting-6",
        ("uniden-sds150-stock",),
        "RH789 fully extended keeps the entire 450-470 MHz block under 1.9:1, the "
        "best single result of the whole survey outside the 800 MHz block.",
    ),
    Recommendation(
        "T-band (470-512 MHz)",
        ("t-band",),
        "rh789:setting-3",
        (),
        "RH789 at setting 3 is the only configuration with a broad T-band match.",
    ),
    Recommendation(
        "1.25m / 222-225 MHz",
        ("1.25m",),
        "tid-td771",
        ("diamond-srh77ca",),
        "The TD771 is excellent across the whole allocation; the Diamond SRH77CA is "
        "a close and equally hands-off alternate.",
    ),
    Recommendation(
        "70cm / 420-450 MHz",
        ("70cm",),
        "diamond-srh77ca",
        ("uniden-sds150-stock",),
        "The Diamond is the strongest broad choice. The stock antenna is useful "
        "near the lower band edge only.",
    ),
    Recommendation(
        "Military air (225-400 MHz)",
        ("military-air",),
        None,
        ("remtronix-920", "generic-extendable:setting-2", "diamond-srh77ca"),
        "No tested antenna covers this 175 MHz-wide range evenly. Pick by "
        "sub-range: Remtronix 920 near 296 MHz, generic extendable setting 2 near "
        "271 MHz, Diamond SRH77CA near 227.5 MHz.",
    ),
    Recommendation(
        "FM broadcast (88-108 MHz)",
        ("fm-broadcast",),
        None,
        ("rh789:setting-2", "generic-extendable:setting-2"),
        "Both options are narrow and geometry-sensitive: RH789 setting 2 near "
        "97.66 MHz, generic extendable setting 2 near 101.25 MHz. Neither matches "
        "the whole broadcast band.",
    ),
    Recommendation(
        "UAT 978 MHz and ADS-B 1090 MHz",
        ("uat-978", "ads-b-1090"),
        "remtronix-920",
        (),
        "Best of the tested set but only a moderate match, and a moderate match is "
        "not the same as usable aircraft-tracking sensitivity.",
    ),
    Recommendation(
        "Civil air (118-137 MHz), 2m, and 6m",
        ("civil-air", "2m", "6m"),
        None,
        (),
        "Nothing tested matched these bands in this no-radio-chassis fixture. No "
        "recommendation is made; do not read a winner into the rankings here.",
    ),
)

BEST_SINGLE = {
    "public_safety": "remtronix-920",
    "widest": "rh789",
}
BEST_PAIR = ("remtronix-920", "rh789")


@dataclass
class Trace:
    frequency_hz: np.ndarray
    gamma: np.ndarray

    @property
    def magnitude(self) -> np.ndarray:
        return np.abs(self.gamma)

    @property
    def swr(self) -> np.ndarray:
        magnitude = self.magnitude
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(magnitude < 1.0, (1.0 + magnitude) / (1.0 - magnitude), np.inf)

    @property
    def return_loss_db(self) -> np.ndarray:
        with np.errstate(divide="ignore", invalid="ignore"):
            return -20.0 * np.log10(self.magnitude)

    @property
    def impedance(self) -> np.ndarray:
        with np.errstate(divide="ignore", invalid="ignore"):
            return REFERENCE_OHMS * (1.0 + self.gamma) / (1.0 - self.gamma)


@dataclass
class ConfigData:
    family: Family
    config: Config
    broadband: Trace
    zooms: Dict[str, Trace] = field(default_factory=dict)


def parse_touchstone(path: Path) -> Trace:
    unit_scale = 1.0
    data_format = "ri"
    rows: List[Tuple[float, float, float]] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.split("!", 1)[0].strip()
        if not line:
            continue
        if line.startswith("#"):
            tokens = line[1:].lower().split()
            scales = {"hz": 1.0, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
            unit_scale = next((scales[token] for token in tokens if token in scales), unit_scale)
            data_format = next((token for token in tokens if token in {"ri", "ma", "db"}), data_format)
            continue
        values = line.replace(",", " ").split()
        if len(values) >= 3:
            rows.append((float(values[0]) * unit_scale, float(values[1]), float(values[2])))
    if not rows:
        raise ValueError(f"No S11 rows in {path}")
    values = np.asarray(rows, dtype=float)
    if data_format == "ri":
        gamma = values[:, 1] + 1j * values[:, 2]
    elif data_format == "ma":
        gamma = values[:, 1] * np.exp(1j * np.deg2rad(values[:, 2]))
    else:
        gamma = (10.0 ** (values[:, 1] / 20.0)) * np.exp(1j * np.deg2rad(values[:, 2]))
    return Trace(values[:, 0], gamma)


def load_data(root: Path) -> Dict[str, ConfigData]:
    antennas = root / "antennas"
    loaded: Dict[str, ConfigData] = {}
    for family in VALID_FAMILIES:
        for config in family.configs:
            directory = antennas / config.directory
            broadband = parse_touchstone(directory / "antenna.s1p")
            zooms: Dict[str, Trace] = {}
            zoom_dir = directory / "zooms"
            if zoom_dir.exists():
                for path in sorted(zoom_dir.glob("*.s1p")):
                    if path.stem in SERVICE_BY_KEY:
                        zooms[path.stem] = parse_touchstone(path)
            loaded[config.key] = ConfigData(family, config, broadband, zooms)
    return loaded


def trace_for_service(data: ConfigData, service: Service) -> Tuple[Trace, str]:
    if service.key in data.zooms:
        return data.zooms[service.key], "averaged_zoom"
    mask = (
        (data.broadband.frequency_hz >= service.start_hz)
        & (data.broadband.frequency_hz <= service.stop_hz)
    )
    if not np.any(mask):
        raise ValueError(f"No broadband points for {data.config.key} / {service.key}")
    return Trace(data.broadband.frequency_hz[mask], data.broadband.gamma[mask]), "broadband"


def finite_or_none(value: float) -> Optional[float]:
    return float(value) if math.isfinite(float(value)) else None


def analyze_trace(trace: Trace) -> Dict[str, object]:
    swr = trace.swr
    finite = np.isfinite(swr)
    if np.any(finite):
        finite_indices = np.flatnonzero(finite)
        local_min = int(np.argmin(swr[finite]))
        minimum_index = int(finite_indices[local_min])
        minimum = float(swr[minimum_index])
        minimum_frequency = float(trace.frequency_hz[minimum_index])
        impedance = trace.impedance[minimum_index]
        resistance = finite_or_none(float(np.real(impedance)))
        reactance = finite_or_none(float(np.imag(impedance)))
        return_loss = finite_or_none(float(trace.return_loss_db[minimum_index]))
    else:
        minimum = math.inf
        minimum_frequency = math.nan
        resistance = None
        reactance = None
        return_loss = None
    return {
        "points": int(len(swr)),
        "minimum_swr": finite_or_none(minimum),
        "minimum_swr_frequency_hz": finite_or_none(minimum_frequency),
        "median_swr": finite_or_none(float(np.median(swr))),
        "maximum_swr": finite_or_none(float(np.max(swr))),
        "coverage_at_or_below_2_percent": float(np.count_nonzero(swr <= 2.0) * 100.0 / len(swr)),
        "coverage_at_or_below_3_percent": float(np.count_nonzero(swr <= 3.0) * 100.0 / len(swr)),
        "resistance_at_minimum_ohm": resistance,
        "reactance_at_minimum_ohm": reactance,
        "return_loss_at_minimum_swr_db": return_loss,
    }


def build_rows(data: Dict[str, ConfigData]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for config_key in VALID_CONFIG_KEYS:
        config_data = data[config_key]
        for service in SERVICES:
            trace, source = trace_for_service(config_data, service)
            row: Dict[str, object] = {
                "family": config_data.family.key,
                "family_label": config_data.family.label,
                "configuration": config_data.config.key,
                "configuration_label": config_data.config.label,
                "service": service.key,
                "service_label": service.label,
                "start_hz": service.start_hz,
                "stop_hz": service.stop_hz,
                "source": source,
            }
            row.update(analyze_trace(trace))
            rows.append(row)
    for service in SERVICES:
        service_rows = [row for row in rows if row["service"] == service.key]
        service_rows.sort(
            key=lambda row: tuple(
                float(row[name]) if row[name] is not None else math.inf
                for name in ("median_swr", "maximum_swr", "minimum_swr")
            )
        )
        for rank, row in enumerate(service_rows, 1):
            row["rank"] = rank
    return rows


def json_ready(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def display_number(value: object, digits: int = 2) -> str:
    if value is None or not math.isfinite(float(value)):
        return VERY_POOR
    return f"{float(value):.{digits}f}"


def short_number(value: object, digits: int = 2) -> str:
    if value is None or not math.isfinite(float(value)):
        return "very poor"
    return f"{float(value):.{digits}f}"


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        path,
        dpi=FIGURE_DPI,
        bbox_inches="tight",
        metadata={"Software": "generate_scanner_antenna_report.py"},
    )
    plt.close(fig)


def style_axis(axis: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    axis.set_title(title, loc="left", fontweight="bold")
    axis.set_xlabel(xlabel)
    axis.set_ylabel(ylabel)
    axis.grid(True, alpha=0.55, linewidth=0.7)
    axis.spines[["top", "right"]].set_visible(False)


def clipped_swr(trace: Trace, maximum: float = 10.0) -> np.ndarray:
    return np.minimum(np.nan_to_num(trace.swr, nan=maximum, posinf=maximum), maximum)


def family_rows(rows: Sequence[Dict[str, object]], family_key: str) -> List[Dict[str, object]]:
    return [row for row in rows if row["family"] == family_key]


def best_family_rows(rows: Sequence[Dict[str, object]], family: Family) -> List[Dict[str, object]]:
    output = []
    candidates = family_rows(rows, family.key)
    for service in SERVICES:
        matching = [row for row in candidates if row["service"] == service.key]
        output.append(
            min(
                matching,
                key=lambda row: tuple(
                    float(row[name]) if row[name] is not None else math.inf
                    for name in ("median_swr", "maximum_swr", "minimum_swr")
                ),
            )
        )
    return output


def plot_broadband(family: Family, data: Dict[str, ConfigData], output: Path) -> None:
    fig, axis = plt.subplots(figsize=(12.4, 5.7))
    for index, config in enumerate(family.configs):
        trace = data[config.key].broadband
        stride = max(1, len(trace.frequency_hz) // 6000)
        axis.plot(
            trace.frequency_hz[::stride] / 1e6,
            clipped_swr(trace)[::stride],
            color=SERIES_COLORS[index % len(SERIES_COLORS)],
            linewidth=1.25,
            label=config.label,
        )
    axis.axhline(2, color="#16a34a", linestyle="--", linewidth=1, label="2:1")
    axis.axhline(3, color="#f59e0b", linestyle=":", linewidth=1, label="3:1")
    style_axis(axis, f"{family.label} · calibrated broadband overview", "Frequency (MHz)", "SWR (clipped at 10:1)")
    axis.set_xlim(50, 1200)
    axis.set_ylim(1, 10)
    axis.legend(ncol=min(4, len(family.configs) + 2), fontsize=8, frameon=False)
    fig.tight_layout()
    save_figure(fig, output)


def plot_scorecard(
    family: Family, rows: Sequence[Dict[str, object]], output: Path
) -> None:
    selected = best_family_rows(rows, family)
    values = [min(float(row["median_swr"] or 10), 10) for row in selected]
    colors = ["#23856d" if value <= 2 else "#b26a22" if value <= 3 else "#b11f4b" for value in values]
    fig, axis = plt.subplots(figsize=(12.4, 7.4))
    positions = np.arange(len(SERVICES))
    axis.barh(positions, values, color=colors)
    axis.set_yticks(positions, [service.label for service in SERVICES], fontsize=8)
    axis.invert_yaxis()
    axis.axvline(2, color="#16a34a", linestyle="--")
    axis.axvline(3, color="#f59e0b", linestyle=":")
    style_axis(axis, f"{family.label} · best setting median by service", "Median SWR (clipped at 10:1)")
    axis.set_xlim(1, 10)
    for position, (value, row) in enumerate(zip(values, selected)):
        label = f"{short_number(row['median_swr'])} · {row['configuration_label']}"
        axis.text(min(value + 0.12, 9.2), position, label, va="center", fontsize=7)
    fig.tight_layout()
    save_figure(fig, output)


def plot_zoom_panels(family: Family, data: Dict[str, ConfigData], output: Path) -> None:
    zoom_entries = [
        (config, service_key, trace)
        for config in family.configs
        for service_key, trace in data[config.key].zooms.items()
    ]
    columns = 2
    rows_count = max(1, math.ceil(len(zoom_entries) / columns))
    fig, axes = plt.subplots(rows_count, columns, figsize=(12.4, 3.2 * rows_count), squeeze=False)
    for axis, entry in zip(axes.flat, zoom_entries):
        config, service_key, trace = entry
        axis.plot(trace.frequency_hz / 1e6, clipped_swr(trace, 8), color="#315c8c", linewidth=1.25)
        axis.axhline(2, color="#16a34a", linestyle="--", linewidth=0.8)
        axis.axhline(3, color="#f59e0b", linestyle=":", linewidth=0.8)
        style_axis(
            axis,
            f"{SERVICE_BY_KEY[service_key].label} · {config.label}",
            "MHz",
            "SWR ≤8",
        )
        axis.set_ylim(1, 8)
    for axis in list(axes.flat)[len(zoom_entries):]:
        axis.set_visible(False)
    fig.suptitle(f"{family.label} · authoritative three-pass averaged zooms", fontweight="bold", x=0.02, ha="left")
    fig.tight_layout()
    save_figure(fig, output)


def plot_impedance_return_loss(family: Family, data: Dict[str, ConfigData], output: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(12.4, 8.2), sharex=True)
    for index, config in enumerate(family.configs):
        trace = data[config.key].broadband
        stride = max(1, len(trace.frequency_hz) // 5000)
        frequency = trace.frequency_hz[::stride] / 1e6
        impedance = trace.impedance[::stride]
        color = SERIES_COLORS[index % len(SERIES_COLORS)]
        axes[0].plot(frequency, np.clip(np.real(impedance), -200, 300), color=color, linewidth=1, label=config.label)
        axes[0].plot(frequency, np.clip(np.imag(impedance), -200, 300), color=color, linewidth=0.8, alpha=0.55)
        axes[1].plot(frequency, np.clip(trace.return_loss_db[::stride], 0, 35), color=color, linewidth=1, label=config.label)
    style_axis(axes[0], f"{family.label} · impedance", ylabel="R solid / X faint (Ω, clipped)")
    axes[0].axhline(50, color="#919191", linestyle="--", linewidth=0.8)
    style_axis(axes[1], "Return loss", "Frequency (MHz)", "Return loss (dB, clipped)")
    axes[1].set_xlim(50, 1200)
    axes[1].legend(ncol=min(5, len(family.configs)), fontsize=8, frameon=False)
    fig.tight_layout()
    save_figure(fig, output)


def heatmap_matrix(
    rows: Sequence[Dict[str, object]], config_keys: Sequence[str]
) -> np.ndarray:
    matrix = np.full((len(config_keys), len(SERVICES)), np.nan)
    lookup = {(row["configuration"], row["service"]): row for row in rows}
    for row_index, config_key in enumerate(config_keys):
        for column_index, service in enumerate(SERVICES):
            value = lookup[(config_key, service.key)]["median_swr"]
            matrix[row_index, column_index] = min(float(value), HEATMAP_VMAX) if value is not None else HEATMAP_VMAX
    return matrix


def plot_heatmap(
    matrix: np.ndarray,
    row_labels: Sequence[str],
    title: str,
    output: Path,
    figsize: Tuple[float, float] = (15.2, 7.0),
) -> None:
    cmap = LinearSegmentedColormap.from_list("swr", ["#23856d", "#f2cf66", "#b11f4b"])
    fig, axis = plt.subplots(figsize=figsize)
    image = axis.imshow(matrix, aspect="auto", cmap=cmap, vmin=HEATMAP_VMIN, vmax=HEATMAP_VMAX)
    axis.set_xticks(np.arange(len(SERVICES)), [service.label for service in SERVICES], rotation=55, ha="right", fontsize=8)
    axis.set_yticks(np.arange(len(row_labels)), row_labels, fontsize=8)
    axis.set_title(title, loc="left", fontweight="bold")
    for row_index in range(matrix.shape[0]):
        for column_index in range(matrix.shape[1]):
            value = matrix[row_index, column_index]
            axis.text(column_index, row_index, f"{value:.1f}" if value < HEATMAP_VMAX else "6+", ha="center", va="center", fontsize=6)
    colorbar = fig.colorbar(image, ax=axis, fraction=0.02, pad=0.02)
    colorbar.set_label("Median SWR (6+ clipped)")
    fig.tight_layout()
    save_figure(fig, output)


def write_best_settings(
    family: Family, rows: Sequence[Dict[str, object]], output: Path
) -> List[Dict[str, object]]:
    selected = best_family_rows(rows, family)
    fields = [
        "service",
        "service_label",
        "configuration",
        "configuration_label",
        "source",
        "minimum_swr",
        "median_swr",
        "maximum_swr",
        "coverage_at_or_below_2_percent",
        "coverage_at_or_below_3_percent",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in selected:
            writer.writerow({field: row[field] if row[field] is not None else VERY_POOR for field in fields})
    return selected


def source_link(config: Config) -> str:
    return f"{Path(config.directory).relative_to(Path(config.directory).parts[0])}/antenna.s1p"


def family_readme(
    family: Family,
    rows: Sequence[Dict[str, object]],
    output: Path,
    best_settings: Optional[Sequence[Dict[str, object]]] = None,
) -> None:
    lines = [
        f"# {family.label}",
        "",
        family.overview,
        "",
        "> **SWR is impedance match only.** It does not measure receive gain, sensitivity, radiation pattern, or on-air decoding.",
        "",
        "## Measurement inventory",
        "",
        f"- Connection: {family.connection}.",
        "- Calibrated 50-1200 MHz broadband sweep: 40,001 points (~28.75 kHz spacing).",
        "- Three-pass complex-averaged service zooms override broadband data for the same configuration and service.",
    ]
    for config in family.configs:
        lines.append(f"- [{config.label}]({source_link(config)}): {config.note}")
    lines.extend(["", "## Conclusions", ""])
    if family.key == "remtronix-920":
        lines.extend([
            "- Best typical modern 700/800/900 MHz public-safety choice.",
            "- Averaged 800 MHz: 1.11 minimum, 1.17 median; averaged 700 MHz stays below 1.82.",
            "- Good across 902-928 MHz and useful at 935-941 MHz; UAT/ADS-B is moderate.",
            "- Military-air response is narrow, centered near 296 MHz—not broad military-air coverage.",
        ])
    elif family.key == "rh789":
        lines.extend([
            "- Setting 5: 150-174 MHz, marine, railroad, and NOAA.",
            "- Setting 4: federal UHF; setting 6: 450-470 MHz (1.09 minimum, below 1.88 across the band).",
            "- Setting 3: T-band; setting 2: a narrow FM response.",
            "- Poor at 700/800/900 MHz regardless of setting.",
        ])
    elif family.key == "tid-td771":
        lines.extend([
            "- Outstanding across all of 222-225 MHz: approximately 1.23-1.31 SWR.",
            "- Other useful responses are narrow, near 225 and 422 MHz.",
        ])
    elif family.key == "diamond-srh77ca":
        lines.extend([
            "- Full 222-225 MHz allocation is approximately 1.33-1.46 SWR.",
            "- Broadly useful across 420-450 MHz: minimum 1.46, median 1.86.",
        ])
    elif family.key == "generic-extendable":
        lines.extend([
            "- Experimental and geometry-sensitive; later averaged zooms shifted after power cycles and are authoritative.",
            "- Setting 2 has narrow responses near 101.25 MHz FM and 271.39 MHz military air.",
            "- The later setting 1 UHF zoom is poor. Do not recommend this whip over stable choices.",
        ])
    else:
        lines.extend([
            "- Useful around 406-470 MHz, strongest at the 420 MHz edge.",
            "- Poor at VHF and 700/800 MHz in this no-radio-chassis fixture.",
        ])
    lines.extend(["", "## Analysis charts", ""])
    chart_entries = [
        ("Broadband overview", "charts/broadband-overview.png"),
        ("Scanner scorecard", "charts/scanner-scorecard.png"),
        ("Authoritative averaged zoom panels", "charts/authoritative-zoom-panels.png"),
        ("Impedance and return loss", "charts/impedance-return-loss.png"),
    ]
    if family.kind == "telescopic":
        chart_entries.append(("Setting × service heatmap", "charts/setting-service-heatmap.png"))
    for label, path in chart_entries:
        lines.extend([f"### {label}", "", f"![{family.short_label} {label}]({path})", ""])
    if best_settings is not None:
        lines.extend([
            "## Best measured setting by service",
            "",
            "[Download CSV](best-setting-table.csv). Rankings use authoritative median SWR, then maximum, then minimum.",
            "",
            "| Service | Setting | Source | Min | Median | Max |",
            "|---|---|---|---:|---:|---:|",
        ])
        for row in best_settings:
            lines.append(
                f"| {row['service_label']} | {row['configuration_label']} | {row['source']} | "
                f"{short_number(row['minimum_swr'])} | {short_number(row['median_swr'])} | "
                f"{short_number(row['maximum_swr'])} |"
            )
    lines.extend(["", "## Caveats", ""])
    lines.extend(f"- {caution}" for caution in family.cautions)
    lines.extend([
        "- Fixed upright bench geometry, no added counterpoise; the USB cable remained part of the RF environment.",
        "- Handheld antennas normally interact with the scanner chassis and operator. Treat these as fixture-specific comparisons.",
        "- [Package method and calibration notes](../../README.md) · [immutable historical manual testing](../../manual-testing/)",
        "",
    ])
    output.write_text("\n".join(lines), encoding="utf-8")


def invalid_readme(family: Family, output: Path) -> None:
    config = family.configs[0]
    text = f"""# {family.label} — invalid / inconclusive

> **Excluded from every scorecard, chart, ranking, and recommendation.**

{family.overview}

## Why this capture is invalid

{family.invalid_reason}

The raw capture is preserved for traceability:

- [antenna.s1p]({source_link(config)})
- [antenna_raw.npz](measurements/2026-08-16/antenna_raw.npz)
- [summary.json](measurements/2026-08-16/summary.json)

No repeat verification was performed because the user skipped it. These files must not be interpreted as antenna performance. A new, reseated capture plus verification would be required before including this model.

SWR is impedance match only—not receive gain, sensitivity, pattern, or decoding performance.
"""
    output.write_text(text, encoding="utf-8")


def write_scorecards(rows: Sequence[Dict[str, object]], comparison: Path) -> None:
    comparison.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "family",
        "family_label",
        "configuration",
        "configuration_label",
        "service",
        "service_label",
        "start_hz",
        "stop_hz",
        "source",
        "points",
        "minimum_swr",
        "minimum_swr_frequency_hz",
        "median_swr",
        "maximum_swr",
        "coverage_at_or_below_2_percent",
        "coverage_at_or_below_3_percent",
        "resistance_at_minimum_ohm",
        "reactance_at_minimum_ohm",
        "return_loss_at_minimum_swr_db",
    ]
    with (comparison / "scanner-band-scorecard.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                field: row[field] if row[field] is not None else VERY_POOR
                for field in fieldnames
            })
    payload = {
        "$schema": SCHEMA_ID,
        "description": "Valid measured configurations only; TIDRADIO H9 stock is excluded as invalid/inconclusive.",
        "reference_impedance_ohm": REFERENCE_OHMS,
        "ranking": ["median_swr", "maximum_swr", "minimum_swr"],
        "nonfinite_display": VERY_POOR,
        "services": [
            {
                "key": service.key,
                "label": service.label,
                "start_hz": service.start_hz,
                "stop_hz": service.stop_hz,
            }
            for service in SERVICES
        ],
        "results": list(rows),
    }
    (comparison / "scanner-band-scorecard.json").write_text(
        json.dumps(json_ready(payload), indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def plot_comparisons(
    data: Dict[str, ConfigData], rows: Sequence[Dict[str, object]], comparison: Path
) -> None:
    best = [min((row for row in rows if row["service"] == service.key), key=lambda row: int(row["rank"])) for service in SERVICES]
    fig, axis = plt.subplots(figsize=(13.5, 7.4))
    positions = np.arange(len(best))
    values = [min(float(row["median_swr"] or 10), 10) for row in best]
    colors = [SERIES_COLORS[list(FAMILY_BY_KEY).index(str(row["family"])) % len(SERIES_COLORS)] for row in best]
    axis.barh(positions, values, color=colors)
    axis.set_yticks(positions, [service.label for service in SERVICES], fontsize=8)
    axis.invert_yaxis()
    axis.axvline(2, color="#16a34a", linestyle="--")
    axis.axvline(3, color="#f59e0b", linestyle=":")
    style_axis(
        axis,
        "Numerically lowest measured median by service (not a recommendation)",
        "Authoritative median SWR (10+ clipped)",
    )
    axis.set_xlim(1, 10)
    for position, row in enumerate(best):
        axis.text(min(values[position] + .12, 8.8), position, f"{row['family_label']} · {row['configuration_label']}", va="center", fontsize=7)
    fig.tight_layout()
    save_figure(fig, comparison / "best-config-by-service.png")

    labels = [f"{CONFIG_FAMILY[key].short_label} · {CONFIG_BY_KEY[key].label}" for key in VALID_CONFIG_KEYS]
    plot_heatmap(
        heatmap_matrix(rows, VALID_CONFIG_KEYS),
        labels,
        "All valid configurations · authoritative median SWR",
        comparison / "all-config-heatmap.png",
        (16.5, 10.2),
    )
    for family_key, filename in (
        ("rh789", "rh789-heatmap.png"),
        ("generic-extendable", "generic-heatmap.png"),
    ):
        family = FAMILY_BY_KEY[family_key]
        keys = [config.key for config in family.configs]
        plot_heatmap(
            heatmap_matrix(rows, keys),
            [config.label for config in family.configs],
            f"{family.label} · setting × service median SWR",
            comparison / filename,
        )

    circumstances = [recommendation.circumstance for recommendation in RECOMMENDATIONS]
    fig, axis = plt.subplots(figsize=(13.5, 7.2))
    axis.set_xlim(0, 1)
    axis.set_ylim(-0.5, len(circumstances) - 0.5)
    axis.axis("off")
    for index, recommendation in enumerate(reversed(RECOMMENDATIONS)):
        y = index
        primary = CONFIG_BY_KEY[recommendation.primary].label if recommendation.primary in CONFIG_BY_KEY else "No broad winner"
        family = CONFIG_FAMILY[recommendation.primary].short_label if recommendation.primary in CONFIG_FAMILY else ""
        label = f"{family} · {primary}".strip(" ·")
        axis.add_patch(plt.Rectangle((0.46, y - .32), .5, .64, color="#f5f5f5", ec="#dedede"))
        axis.text(0.01, y, recommendation.circumstance, va="center", fontsize=8.5, fontweight="bold")
        axis.text(0.48, y, label, va="center", fontsize=8.5, color="#b11f4b" if recommendation.primary else "#5c5c5c")
    axis.set_title("Practical recommendation map", loc="left", fontweight="bold")
    fig.tight_layout()
    save_figure(fig, comparison / "practical-recommendations.png")


def recommendation_table() -> List[str]:
    lines = [
        "| Circumstance | Primary recommendation | Alternate / qualification |",
        "|---|---|---|",
    ]
    for recommendation in RECOMMENDATIONS:
        if recommendation.primary:
            config = CONFIG_BY_KEY[recommendation.primary]
            primary = f"{CONFIG_FAMILY[recommendation.primary].short_label} — {config.label}"
        else:
            primary = "No broad measured winner"
        alternates = ", ".join(
            f"{CONFIG_FAMILY[key].short_label} — {CONFIG_BY_KEY[key].label}"
            for key in recommendation.alternates
        )
        qualification = recommendation.guidance
        if alternates:
            qualification = f"Alternate(s): {alternates}. {qualification}"
        lines.append(f"| {recommendation.circumstance} | {primary} | {qualification} |")
    return lines


def comparison_readme(output: Path) -> None:
    lines = [
        "# Scanner antenna comparison",
        "",
        "> **SWR is impedance match only—not receive gain, sensitivity, radiation pattern, or decoded-signal performance.**",
        "",
        "Rankings use the authoritative median SWR, then maximum, then minimum. An exact service/configuration averaged zoom overrides broadband data. The invalid TIDRADIO H9 stock capture is excluded.",
        "",
        "## Circumstance table",
        "",
        *recommendation_table(),
        "",
        "## Best one antenna",
        "",
        "**Remtronix 920** for typical SDS150 modern public-safety trunking. It is the clear measured choice for 700/800 MHz and remains useful through 900 MHz.",
        "",
        "Choose the **RH789** instead when manual retuning and broad VHF/UHF flexibility matter more. It covers more legacy and conventional services at the right settings, but misses 700/800/900 MHz.",
        "",
        "## Best two-antenna combination",
        "",
        "**Remtronix 920 + RH789.** The pair combines modern trunking with manually tuned VHF/UHF flexibility. Substitute or add the **TD771** when 222-225 MHz is the priority; use the **Diamond SRH77CA** when broad 420-450 MHz performance is the priority.",
        "",
        "## Files and charts",
        "",
        "- [CSV scorecard](scanner-band-scorecard.csv) · [standards-compliant JSON](scanner-band-scorecard.json)",
        "- [Offline interactive report](interactive-report.html)",
        "",
        "![Numerically lowest measured median by service](best-config-by-service.png)",
        "",
        "The chart above shows the lowest measured median even when every option is",
        "poor. Use the circumstance table—not this raw numerical rank—for practical",
        "antenna selection.",
        "",
        "![All configuration heatmap](all-config-heatmap.png)",
        "",
        "![RH789 heatmap](rh789-heatmap.png)",
        "",
        "![Generic extendable heatmap](generic-heatmap.png)",
        "",
        "![Practical recommendations](practical-recommendations.png)",
        "",
        "Civil air and 2m have no good measured winner in this no-radio-chassis fixture. Military air consists of split, narrow resonances rather than one broad solution.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


THEME_SCRIPT = """  (() => {
    const param = new URLSearchParams(window.location.search).get("scoutTheme");
    const theme =
      param || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  })();"""

THEME_VARIABLES = """:root {
  color-scheme: light;
  --cp-bg: #f7f4ef;
  --cp-bg-elevated: #fcfbf8;
  --cp-surface: #ffffff;
  --cp-surface-soft: #f5f5f5;
  --cp-border: #dedede;
  --cp-border-strong: #919191;
  --cp-text: #242424;
  --cp-text-muted: #5c5c5c;
  --cp-text-soft: #6f6f6f;
  --cp-accent: #b11f4b;
  --cp-accent-hover: #9a1a41;
  --cp-accent-soft: rgba(177, 31, 75, 0.08);
  --cp-accent-fg: #ffffff;
  --cp-success: #16a34a;
  --cp-danger: #dc2626;
  --cp-warning: #f59e0b;
  --cp-link: #0078d4;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.12);
  --cp-overlay: rgba(255, 255, 255, 0.8);
  --cp-panel: rgba(255, 255, 255, 0.86);
  --cp-panel-strong: rgba(255, 255, 255, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.55);
  --cp-highlight: rgba(177, 31, 75, 0.12);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --cp-bg: #3d3b3a;
  --cp-bg-elevated: #343231;
  --cp-surface: #292929;
  --cp-surface-soft: #2e2e2e;
  --cp-border: #474747;
  --cp-border-strong: #5f5f5f;
  --cp-text: #dedede;
  --cp-text-muted: #919191;
  --cp-text-soft: #b0b0b0;
  --cp-accent: #fd8ea1;
  --cp-accent-hover: #fb7b91;
  --cp-accent-soft: rgba(253, 142, 161, 0.14);
  --cp-accent-fg: #1a1a1a;
  --cp-success: #4ade80;
  --cp-danger: #f87171;
  --cp-warning: #fbbf24;
  --cp-link: #4da6ff;
  --cp-shadow: 0 18px 48px rgba(0, 0, 0, 0.32);
  --cp-overlay: rgba(41, 41, 41, 0.88);
  --cp-panel: rgba(41, 41, 41, 0.72);
  --cp-panel-strong: rgba(41, 41, 41, 0.96);
  --cp-sheen: rgba(255, 255, 255, 0.04);
  --cp-highlight: rgba(253, 142, 161, 0.12);
}"""


def interactive_report(rows: Sequence[Dict[str, object]], output: Path) -> None:
    payload = json.dumps(json_ready(list(rows)), separators=(",", ":"), allow_nan=False)
    families = json.dumps([
        {"key": family.key, "label": family.label}
        for family in VALID_FAMILIES
    ], separators=(",", ":"))
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SDS150 scanner antenna comparison</title>
<link rel="icon" href="data:,">
<script>
{THEME_SCRIPT}
</script>
<style>
{THEME_VARIABLES}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--cp-bg); color:var(--cp-text); font-family:"Segoe UI", Aptos, Calibri, -apple-system, BlinkMacSystemFont, sans-serif; }}
.shell {{ max-width:1400px; margin:auto; padding:32px 24px 64px; }}
h1 {{ margin:.15em 0; font-size:clamp(2rem,5vw,3.4rem); letter-spacing:-.04em; }}
h2 {{ margin-top:0; }} p {{ color:var(--cp-text-muted); line-height:1.55; }}
.eyebrow {{ color:var(--cp-accent); font-weight:700; letter-spacing:.12em; text-transform:uppercase; }}
.controls {{ display:flex; gap:14px; flex-wrap:wrap; margin:24px 0; }}
label {{ display:grid; gap:6px; color:var(--cp-text-muted); font-size:.85rem; }}
select {{ min-width:210px; border:1px solid var(--cp-border-strong); background:var(--cp-surface); color:var(--cp-text); border-radius:10px; padding:10px; font:inherit; }}
.panel {{ background:var(--cp-surface); border:1px solid var(--cp-border); border-radius:16px; box-shadow:var(--cp-shadow); padding:20px; margin:16px 0; }}
.caveat {{ border-left:5px solid var(--cp-warning); background:var(--cp-accent-soft); padding:14px 18px; font-weight:700; }}
canvas {{ width:100%; height:380px; display:block; }}
.table-wrap {{ overflow:auto; }} table {{ width:100%; border-collapse:collapse; font-size:.88rem; }}
th,td {{ padding:10px; border-bottom:1px solid var(--cp-border); text-align:left; white-space:nowrap; }}
th {{ color:var(--cp-text-muted); }} tbody tr:hover {{ background:var(--cp-accent-soft); }}
.source {{ color:var(--cp-link); }} footer {{ color:var(--cp-text-muted); margin-top:28px; }}
</style>
</head>
<body><main class="shell">
<div class="eyebrow">Calibrated NanoVNA-H comparison</div>
<h1>SDS150 scanner antennas</h1>
<p>Explore all 400 valid configuration × service results. Exact averaged zooms override broadband points.</p>
<div class="caveat">SWR is impedance match only—not receive gain, sensitivity, radiation pattern, or on-air decoding. The invalid/inconclusive TIDRADIO H9 stock capture is excluded.</div>
<div class="controls">
<label>Service<select id="service"></select></label>
<label>Family<select id="family"></select></label>
<label>Configuration<select id="config"></select></label>
</div>
<section class="panel"><h2 id="chart-title">Authoritative median SWR</h2><canvas id="chart" width="1200" height="380"></canvas></section>
<section class="panel"><h2>Measured statistics</h2><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Family</th><th>Configuration</th><th>Service</th><th>Source</th><th>Min @ MHz</th><th>Median</th><th>Max</th><th>≤2</th><th>≤3</th><th>R + jX at min</th><th>Return loss</th></tr></thead><tbody id="rows"></tbody></table></div></section>
<footer>Offline, self-contained report · 50 Ω reference · NanoVNA-H 1.2.50 · no network or local storage</footer>
</main>
<script>
const DATA={payload};
const FAMILIES={families};
const SERVICES=[...new Map(DATA.map(r=>[r.service,{{key:r.service,label:r.service_label}}])).values()];
const service=document.querySelector("#service"), family=document.querySelector("#family"), config=document.querySelector("#config");
function options(el,items,all){{el.innerHTML=`<option value="">${{all}}</option>`+items.map(x=>`<option value="${{x.key}}">${{x.label}}</option>`).join("");}}
options(service,SERVICES,"All services"); options(family,FAMILIES,"All families");
function configs(){{const old=config.value; const subset=[...new Map(DATA.filter(r=>!family.value||r.family===family.value).map(r=>[r.configuration,{{key:r.configuration,label:r.configuration_label}}])).values()]; options(config,subset,"All configurations"); if(subset.some(x=>x.key===old))config.value=old;}}
function fmt(v,d=2){{return v===null?"very poor / outside calibrated dynamic range":Number(v).toFixed(d);}}
function filtered(){{return DATA.filter(r=>(!service.value||r.service===service.value)&&(!family.value||r.family===family.value)&&(!config.value||r.configuration===config.value));}}
function draw(rows){{const canvas=document.querySelector("#chart"),ctx=canvas.getContext("2d"),css=getComputedStyle(document.documentElement); const text=css.getPropertyValue("--cp-text").trim(), muted=css.getPropertyValue("--cp-text-muted").trim(), accent=css.getPropertyValue("--cp-accent").trim(), border=css.getPropertyValue("--cp-border").trim(); ctx.clearRect(0,0,canvas.width,canvas.height); const values=rows.slice().sort((a,b)=>(a.median_swr??1e9)-(b.median_swr??1e9)).slice(0,24); if(!values.length)return; const left=270,top=20,rowH=Math.min(28,320/values.length),max=10; ctx.font="12px Segoe UI, Aptos, sans-serif"; values.forEach((r,i)=>{{const y=top+i*rowH,w=Math.max(2,(Math.min(r.median_swr??max,max)-1)/(max-1)*(canvas.width-left-30));ctx.fillStyle=accent;ctx.fillRect(left,y,w,rowH*.62);ctx.fillStyle=text;ctx.textAlign="right";ctx.fillText((service.value?r.family_label+" · "+r.configuration_label:r.service_label+" · "+r.configuration_label).slice(0,42),left-8,y+12);ctx.textAlign="left";ctx.fillText(fmt(r.median_swr),left+w+6,y+12);}});ctx.strokeStyle=border;ctx.beginPath();ctx.moveTo(left,top-5);ctx.lineTo(left,top+values.length*rowH);ctx.stroke();ctx.fillStyle=muted;ctx.fillText("Median SWR · 10+ clipped",left,canvas.height-12);}}
function render(){{const rows=filtered().sort((a,b)=>a.service.localeCompare(b.service)||a.rank-b.rank);draw(rows);document.querySelector("#rows").innerHTML=rows.map(r=>`<tr><td>${{r.rank}}</td><td>${{r.family_label}}</td><td>${{r.configuration_label}}</td><td>${{r.service_label}}</td><td class="source">${{r.source}}</td><td>${{fmt(r.minimum_swr)}} @ ${{r.minimum_swr_frequency_hz===null?"—":(r.minimum_swr_frequency_hz/1e6).toFixed(3)}}</td><td>${{fmt(r.median_swr)}}</td><td>${{fmt(r.maximum_swr)}}</td><td>${{fmt(r.coverage_at_or_below_2_percent,1)}}%</td><td>${{fmt(r.coverage_at_or_below_3_percent,1)}}%</td><td>${{fmt(r.resistance_at_minimum_ohm,1)}} + j${{fmt(r.reactance_at_minimum_ohm,1)}} Ω</td><td>${{fmt(r.return_loss_at_minimum_swr_db,1)}} dB</td></tr>`).join("");}}
family.addEventListener("change",()=>{{configs();render();}}); service.addEventListener("change",render); config.addEventListener("change",render); window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change",render); configs();render();
</script></body></html>
"""
    output.write_text(html, encoding="utf-8")


def package_readme(root: Path) -> None:
    inventory = [
        ("Remtronix 920", "antennas/remtronix-920/README.md", "valid", "fixed; modern 700/800/900 MHz"),
        ("RH789", "antennas/rh789/README.md", "valid", "settings 1-6; manually retuned VHF/UHF"),
        ("TID TD771", "antennas/tid-td771/README.md", "valid", "fixed; exceptional 222-225 MHz"),
        ("Diamond SRH77CA", "antennas/diamond-srh77ca/README.md", "valid", "fixed; broad 420-450 MHz"),
        ("Generic extendable", "antennas/generic-extendable/README.md", "valid / experimental", "settings 1-10; geometry-sensitive"),
        ("Uniden SDS150 stock", "antennas/uniden-sds150-stock/README.md", "valid", "reference antenna"),
        ("TIDRADIO H9 stock", "antennas/tidradio-h9-stock/README.md", "invalid / inconclusive", "preserved, excluded"),
        ("JYR8010 EFHW", "antennas/jyr8010-efhw/README.md", "preserved HF report", "separate prior report"),
    ]
    lines = [
        "# Antenna measurement results",
        "",
        "Reproducible reports built from calibrated complex S11 measurements. The scanner survey compares six valid antenna families and 20 configurations across 20 receive-service windows; the earlier JYR8010 EFHW HF report remains intact.",
        "",
        "> **SWR is impedance match only.** It cannot establish receive gain, scanner sensitivity, radiation pattern, or decode performance.",
        "",
        "## Headline recommendations",
        "",
        "- **Best one for typical SDS150 modern public safety:** Remtronix 920.",
        "- **Best when manual VHF/UHF retuning matters more:** RH789, while accepting poor 700/800/900 MHz.",
        "- **Best two:** Remtronix 920 + RH789.",
        "- Add/substitute TD771 for 222-225 MHz; choose Diamond SRH77CA for broad 420-450 MHz.",
        "- No good measured winner for civil air or 2m in this no-radio-chassis fixture.",
        "",
        "See the [full comparison and circumstance table](comparison/README.md) or open the [offline interactive report](comparison/interactive-report.html).",
        "",
        "## Inventory",
        "",
        "| Family | Status | Scope |",
        "|---|---|---|",
    ]
    lines.extend(f"| [{name}]({path}) | {status} | {scope} |" for name, path, status, scope in inventory)
    lines.extend([
        "",
        "## Method",
        "",
        "- NanoVNA-H firmware 1.2.50, 50 Ω reference.",
        "- Software ideal OSL calibration at the SMA-to-BNC output reference plane.",
        "- Broadband: 50-1200 MHz, 40,001 points, nominal ~28.75 kHz spacing.",
        "- Service zooms: three complex-S11 passes averaged point by point. An exact configuration/service zoom is authoritative over broadband.",
        "- Every valid configuration × service records minimum SWR and frequency, median, maximum, coverage ≤2:1 and ≤3:1, source, R, X, and return loss derived from RI Touchstone data.",
        "- Ranking: authoritative median SWR, then maximum, then minimum.",
        "- Nonfinite values become JSON `null` and display as “very poor / outside calibrated dynamic range.”",
        "",
        "## Calibration and fixture",
        "",
        "Load reconnect verification: median 1.00135, p95 1.01044, maximum 1.19335 across the full sweep; VHF maximum 1.00127. See the [preserved calibration baseline](calibration-baselines/sma-to-bnc/2026-08-16-nanovna-h/README.md).",
        "",
        "The saved calibration is reusable only with the same unchanged adapter chain and a load verification each session. Calibration accuracy does not remove antenna-fixture uncertainty.",
        "",
        "Measurements used fixed upright geometry, no added counterpoise, with the USB cable remaining part of the RF environment. Handheld antennas depend on the radio chassis, operator, adapter, nearby objects, and cable geometry.",
        "",
        "## Layout and reproduction",
        "",
        "- `antennas/*/measurements/`: preserved S1P, raw NPZ, JSON, and authoritative zoom artifacts.",
        "- `antennas/*/charts/` and family READMEs: generated analysis.",
        "- `comparison/`: CSV/JSON scorecards, charts, recommendations, and offline report.",
        "- `calibration-baselines/`: immutable OSL and verification captures.",
        "- [`manual-testing/`](manual-testing/): immutable historical coarse reconnaissance; not used for current rankings.",
        "- `tools/generate_scanner_antenna_report.py`: deterministic generator.",
        "",
        "```bash",
        "python3 antenna-results/tools/generate_scanner_antenna_report.py",
        "```",
        "",
        "Run this from the repository root in any Python environment with the versions in [`tools/requirements.txt`](tools/requirements.txt).",
        "",
        "## Invalid capture policy",
        "",
        "The TIDRADIO H9 stock trace appeared electrically open and repeat verification was skipped. Raw files are preserved, clearly labeled invalid/inconclusive, and excluded from all calculations and recommendations.",
        "",
    ])
    (root / "README.md").write_text("\n".join(lines), encoding="utf-8")


def calibration_readme(root: Path) -> None:
    path = root / "calibration-baselines/sma-to-bnc/2026-08-16-nanovna-h/README.md"
    text = """# NanoVNA-H SMA-to-BNC calibration baseline — 2026-08-16

Immutable calibration capture used by the scanner-antenna measurements.

## Reference plane and acquisition

- NanoVNA-H firmware 1.2.50; 50 Ω reference.
- 50-1200 MHz, 40,001 points, nominal 28.75 kHz spacing.
- Software ideal open/short/load calibration at the antenna side of the attached SMA-to-BNC adapter.
- The adapter chain must remain physically unchanged.

## Preserved files

- `open.npz` + `open.csv`
- `short.npz` + `short.csv`
- `load.npz` + `load.csv`
- `calibration.npz`
- `verification/load-reconnect-verification.csv`
- `verification/load-reconnect-verification.json`

## Reconnect verification

| Region | Median SWR | p95 SWR | Maximum SWR |
|---|---:|---:|---:|
| Full 50-1200 MHz | 1.00135 | 1.01044 | 1.19335 |
| VHF high 137-225 MHz | 1.00032 | 1.00041 | 1.00127 |

The saved calibration is reusable only with the same unchanged adapter chain and a fresh 50 Ω load verification each session. Recalibrate after reconnecting or moving the chain if verification is not consistent. Fixture geometry still affects handheld antennas even when the reference-plane calibration is accurate.
"""
    path.write_text(text, encoding="utf-8")


def remove_duplicate_derivatives(root: Path) -> None:
    for family in FAMILIES:
        for config in family.configs:
            directory = root / "antennas" / config.directory
            for name in ("antenna_swr.csv", "antenna_raw.csv"):
                duplicate = directory / name
                if duplicate.exists():
                    duplicate.unlink()
            for duplicate in sorted(directory.glob("*.png")):
                duplicate.unlink()


def generate(root: Path) -> Tuple[int, int]:
    remove_duplicate_derivatives(root)
    data = load_data(root)
    rows = build_rows(data)
    comparison = root / "comparison"
    write_scorecards(rows, comparison)
    with plt.rc_context(PLOT_STYLE):
        for family in VALID_FAMILIES:
            directory = root / "antennas" / family.key
            charts = directory / "charts"
            plot_broadband(family, data, charts / "broadband-overview.png")
            plot_scorecard(family, rows, charts / "scanner-scorecard.png")
            plot_zoom_panels(family, data, charts / "authoritative-zoom-panels.png")
            plot_impedance_return_loss(family, data, charts / "impedance-return-loss.png")
            best_settings = None
            if family.kind == "telescopic":
                keys = [config.key for config in family.configs]
                plot_heatmap(
                    heatmap_matrix(rows, keys),
                    [config.label for config in family.configs],
                    f"{family.label} · setting × service median SWR",
                    charts / "setting-service-heatmap.png",
                )
                best_settings = write_best_settings(family, rows, directory / "best-setting-table.csv")
            family_readme(family, rows, directory / "README.md", best_settings)
        plot_comparisons(data, rows, comparison)
    invalid_readme(FAMILY_BY_KEY["tidradio-h9-stock"], root / "antennas/tidradio-h9-stock/README.md")
    comparison_readme(comparison / "README.md")
    interactive_report(rows, comparison / "interactive-report.html")
    package_readme(root)
    calibration_readme(root)
    generated = [
        path for path in root.rglob("*")
        if path.is_file()
        and (
            "/charts/" in path.as_posix()
            or "/comparison/" in path.as_posix()
            or path.name in {"README.md", "best-setting-table.csv"}
        )
        and "/manual-testing/" not in path.as_posix()
        and "/jyr8010-efhw/" not in path.as_posix()
    ]
    return len(generated), sum(path.stat().st_size for path in generated)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="antenna-results directory (default: inferred from this script)",
    )
    arguments = parser.parse_args()
    count, size = generate(arguments.root.resolve())
    print(f"Generated {count} report files ({size:,} bytes) from {len(VALID_CONFIG_KEYS)} valid configurations.")


if __name__ == "__main__":
    main()
