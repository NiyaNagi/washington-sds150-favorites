"""SDS100/SDS150 display palette generation and validation.

The XML shape follows an actual Sentinel export (including Uniden's historic
``UndienScanner`` root spelling). Screen/item names and option codes are kept
separate from palette colors so every palette has an identical, predictable
information layout.
"""
from __future__ import annotations

import colorsys
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from wasds150.display_colors import (
    SUPPORTED_DISPLAY_COLORS,
    SUPPORTED_DISPLAY_COLOR_VALUES,
)


ItemSpec = Tuple[str, Optional[str]]
COLOR_KEYS = ("background", "status", "system", "department", "channel", "metadata", "alert", "accent")

HUGE_OPTION_CHOICES = (
    "Empty", "CTCSS/DCS", "FL_Name", "Frequency", "NumberTag", "SysSubID",
    "ServiceType", "SiteId", "SiteName", "SystemType", "SystemId", "TGID",
    "UnitId", "UnitIdName", "Volume&Squelch", "WACN",
)
LARGE_OPTION_CHOICES = (
    "Empty", "Battery Current", "Battery Temperature", "BattVoltage",
    "CTCSS/DCS", "D_ErrorCount", "FL_Name", "Filter", "Frequency", "latitude",
    "Lcn", "longitude", "Noise", "NumberTag", "SysSubID", "Rssi", "Rssi Bar",
    "ServiceType", "SiteId", "SiteName", "SystemType", "SystemId", "TdmaSlot",
    "TGID", "UnitId", "UnitIdName", "UnitIdName_1", "UnitIdName_2",
    "UnitIdName_3", "UnitIdName_4", "USB2_vbus", "Volume&Squelch", "WACN",
)
SMALL_OPTION_CHOICES = (
    "Empty", "ATT", "Bluetooth", "SCR", "CC", "Day", "P25Status", "GPS",
    "IFX", "Modulation", "P_Ch", "PRI", "REC", "REP", "Squelch",
    "TdmaSlot", "Time", "Volume", "LVL", "WxPRI",
)
ICON_OPTION_CHOICES = (
    "Empty", "Bluetooth", "SCR", "CC", "GPS", "IFX", "Modulation", "P_Ch",
    "PRI", "REC", "REP", "LVL", "WxPRI",
)
DATA_DEDUP_FALLBACKS = (
    "ServiceType", "CTCSS/DCS", "SystemType", "SystemId", "SysSubID", "WACN",
    "SiteName", "SiteId", "Frequency", "TGID", "UnitId", "UnitIdName",
    "NumberTag", "Rssi", "Rssi Bar", "Filter", "Noise", "D_ErrorCount", "Lcn",
    "latitude", "longitude", "BattVoltage", "Battery Current", "Battery Temperature",
    "USB2_vbus", "Volume&Squelch", "TdmaSlot", "FL_Name",
)


def _simple(department_option: str, channel_option: str) -> List[ItemSpec]:
    return [
        ("Func", None), ("Option_1", "ATT"), ("Option_2", "Bluetooth"),
        ("Option_3", "Day"), ("Option_4", "Time"), ("SIG", None), ("BATT", None),
        ("SP0", None), ("Option_5", "Volume"), ("Option_6", "Squelch"),
        ("Option_7", "P25Status"), ("Option_8", "TdmaSlot"), ("key", None), ("Dir", None),
        ("System Name", None), ("System option", "FL_Name"), ("Avoid", None),
        ("Department Name", None), ("Department option", department_option), ("Avoid", None),
        ("Channel Name", None), ("Channel option", channel_option), ("Avoid", None),
        ("Option A", "ServiceType"), ("Option B", "CTCSS/DCS"),
        ("Icon 1", "Modulation"), ("Icon 2", "P_Ch"), ("Icon 3", "IFX"),
        ("Icon 4", "LVL"), ("Icon 5", "Empty"), ("Icon 6", "REC"),
        ("Icon 7", "GPS"), ("Icon 8", "PRI"), ("Icon 9", "CC"), ("Icon 10", "WxPRI"),
        ("Soft1 Key", None), ("SP1", None), ("Soft2 Key", None), ("SP2", None),
        ("Soft3 Key", None),
    ]


def _detail(department_option: str, channel_option: str, detail_b2: str) -> List[ItemSpec]:
    return [
        ("Func", None), ("Option_1", "ATT"), ("Option_2", "Bluetooth"),
        ("Option_3", "Day"), ("Option_4", "Time"), ("SIG", None), ("BATT", None),
        ("Info Area 1", None), ("Option_7", "P25Status"), ("Option_8", "TdmaSlot"),
        ("key", None), ("Dir", None), ("Info Area 2", None),
        ("Option C-1", "Volume&Squelch"), ("Info Area 3", None), ("Option C-2", "NumberTag"),
        ("System Name", None), ("System option", "FL_Name"), ("Avoid", None),
        ("Department Name", None), ("Department option", department_option), ("Avoid", None),
        ("Channel Name", None), ("Channel option", channel_option), ("Avoid", None),
        ("Option A-1", "ServiceType"), ("Option B-1", "CTCSS/DCS"),
        ("Option A-2", "SystemId"), ("Option B-2", detail_b2),
        ("Option A-3", "SysSubID"), ("Option B-3", "SiteId"),
        ("Option A-4", "WACN"), ("Option B-4", "BattVoltage"),
        ("Option A-5", "UnitId"), ("Option B-5", "Rssi"),
        ("Icon 1", "Modulation"), ("Icon 2", "P_Ch"), ("Icon 3", "IFX"),
        ("Icon 4", "LVL"), ("Icon 5", "Empty"), ("Icon 6", "REC"),
        ("Icon 7", "GPS"), ("Icon 8", "PRI"), ("Icon 9", "CC"), ("Icon 10", "WxPRI"),
        ("Soft1 Key", None), ("SP1", None), ("Soft2 Key", None), ("SP2", None),
        ("Soft3 Key", None),
    ]


def _special(kind: str) -> List[ItemSpec]:
    search = kind == "Search"
    return [
        ("Func", None), ("Option_1", "ATT"), ("Option_2", "Bluetooth"),
        ("Option_3", "Day"), ("Option_4", "Time"), ("SIG", None), ("BATT", None),
        ("Info Area 1", None), ("Option_7", "P25Status" if search else "Empty"),
        ("Option_8", "TdmaSlot" if search else "Empty"), ("key", None), ("Dir", None),
        ("Info Area 2", None), ("Option C-1", "Volume&Squelch"), ("Info Area 3", None),
        ("Option C-2", "Empty"), ("Primary Area-1", None), ("Primary Area-2", None),
        ("Primary Area-3", None), ("Sub Info", None), ("Modulation", None),
        ("Avoid", None), ("Hold", None), ("Detail Info", None),
        ("Option A-1", "SystemId" if search else "Empty"), ("Option B-1", "BattVoltage"),
        ("Option A-2", "UnitId" if search else "Empty"), ("Option B-2", "Rssi"),
        ("Option A-3", "TGID" if search else "Empty"), ("Option B-3", "Rssi Bar"),
        ("Icon 1", "SCR" if search else "Empty"), ("Icon 2", "REP" if search else "Empty"),
        ("Icon 3", "IFX"), ("Icon 4", "LVL"), ("Icon 5", "Empty"),
        ("Icon 6", "REC"), ("Icon 7", "GPS"), ("Icon 8", "PRI" if search else "Empty"),
        ("Icon 9", "CC" if search else "Empty"), ("Icon 10", "WxPRI" if search else "Empty"),
        ("Soft1 Key", None), ("SP1", None), ("Soft2 Key", None), ("SP2", None),
        ("Soft3 Key", None),
    ]


SCREEN_SPECS: Dict[str, List[ItemSpec]] = {
    "SimpleConventional": _simple("Empty", "Frequency"),
    "SimpleTrunk": _simple("SiteName", "TGID"),
    "DetailConventional": _detail("Empty", "Frequency", "TGID"),
    "DetailTrunk": _detail("SiteName", "TGID", "Frequency"),
    "Search": _special("Search"),
    "Weather": _special("Weather"),
    "Tone out": _special("Tone out"),
}

_SIMPLE_LAYOUT = (
    ("scanner-status-row", (0, 1, 2, 3, 4, 5, 6), ()),
    ("scanner-utility-row", (7, 8, 9, 10, 11, 12, 13), ()),
    ("scanner-hierarchy-row", (14, 15, 16), (14,)),
    ("scanner-hierarchy-row", (17, 18, 19), (17,)),
    ("scanner-hierarchy-row", (20, 21, 22), (20,)),
    ("scanner-detail-pair", (23, 24), ()),
    ("scanner-icons", tuple(range(25, 35)), ()),
    ("scanner-softkeys", (35, 36, 37, 38, 39), ()),
)
_DETAIL_LAYOUT = (
    ("scanner-status-row", (0, 1, 2, 3, 4, 5, 6), ()),
    ("scanner-info-top", (7, 8, 9, 10, 11), ()),
    ("scanner-info-pair", (12, 13), ()),
    ("scanner-info-pair", (14, 15), ()),
    ("scanner-hierarchy-row", (16, 17, 18), (16,)),
    ("scanner-hierarchy-row", (19, 20, 21), (19,)),
    ("scanner-hierarchy-row", (22, 23, 24), (22,)),
    *(("scanner-detail-pair", (index, index + 1), ()) for index in (25, 27, 29, 31, 33)),
    ("scanner-icons", tuple(range(35, 45)), ()),
    ("scanner-softkeys", (45, 46, 47, 48, 49), ()),
)
_SPECIAL_LAYOUT = (
    ("scanner-status-row", (0, 1, 2, 3, 4, 5, 6), ()),
    ("scanner-info-top", (7, 8, 9, 10, 11), ()),
    ("scanner-info-pair", (12, 13), ()),
    ("scanner-info-pair", (14, 15), ()),
    ("scanner-special-row", (16, 21), (16,)),
    ("scanner-special-row", (17, 22), (17,)),
    ("scanner-special-detail", (18, 19, 20, 23), (18,)),
    *(("scanner-detail-pair", (index, index + 1), ()) for index in (24, 26, 28)),
    ("scanner-icons", tuple(range(30, 40)), ()),
    ("scanner-softkeys", (40, 41, 42, 43, 44), ()),
)


def display_layout_catalog() -> Dict[str, List[dict]]:
    layouts = {}
    for screen_name in SCREEN_SPECS:
        source = (
            _SIMPLE_LAYOUT if screen_name.startswith("Simple")
            else _DETAIL_LAYOUT if screen_name.startswith("Detail")
            else _SPECIAL_LAYOUT
        )
        layouts[screen_name] = [
            {"class_name": class_name, "indices": list(indices), "primary_indices": list(primary_indices)}
            for class_name, indices, primary_indices in source
        ]
    return layouts


@dataclass(frozen=True)
class DisplayPalette:
    id: str
    name: str
    description: str
    background: str
    status: str
    system: str
    department: str
    channel: str
    metadata: str
    alert: str
    accent: str

    def colors(self) -> Dict[str, str]:
        return {
            "background": self.background,
            "status": self.status,
            "system": self.system,
            "department": self.department,
            "channel": self.channel,
            "metadata": self.metadata,
            "alert": self.alert,
            "accent": self.accent,
        }


@dataclass(frozen=True)
class DisplayLayoutTemplate:
    id: str
    name: str
    description: str
    scenario: str
    screen_item_options: Dict[str, str]


@dataclass(frozen=True)
class DisplayColorGrouping:
    id: str
    name: str
    description: str
    style: str
    category_map: Dict[str, str]
    item_categories: Dict[str, str]
    item_color_slots: Optional[Dict[str, int]] = None
    option_color_slots: Optional[Dict[str, int]] = None


PALETTES: Tuple[DisplayPalette, ...] = (
    DisplayPalette(
        "night-ops", "Night Ops", "Cool hierarchy colors on true black for dark cabins and general use.",
        "000000", "FFFFFF", "00BDFF", "FF8800", "FFD600", "E79473", "FF108C", "00FF7B",
    ),
    DisplayPalette(
        "daylight-high-contrast", "Daylight High Contrast", "Dark saturated labels on white for bright outdoor viewing.",
        "FFFFFF", "000000", "000084", "840000", "526B29", "4A007B", "AD2121", "006300",
    ),
    DisplayPalette(
        "colorblind-dark", "Colorblind Dark", "Okabe-Ito-inspired blue, orange, yellow, and purple grouping.",
        "000000", "FFFFFF", "00BDFF", "FFA100", "FFFF00", "D66FD6", "FF7F4A", "00CACE",
    ),
    DisplayPalette(
        "low-light-amber", "Low-Light Amber", "Warm amber hierarchy with restrained red accents to preserve night vision.",
        "000000", "FFF7D6", "FF4600", "FFA100", "FFD600", "E79473", "FF108C", "94CA31",
    ),
    DisplayPalette(
        "oceanic", "Oceanic", "Cool marine blues with warm orange and sand hierarchy accents.",
        "00007B", "FFFFFF", "84CAF7", "FFA100", "FFD600", "D6BDD6", "FF7F4A", "39DECE",
    ),
    DisplayPalette(
        "forest-watch", "Forest Watch", "Natural green field palette with wildfire-ready amber and red accents.",
        "000000", "FFFFFF", "8CEB8C", "FFA100", "FFFF00", "DEE3F7", "EF7F7B", "00FF7B",
    ),
    DisplayPalette(
        "cyber-neon", "Cyber Neon", "High-energy cyan, orange, yellow, and magenta on near-black violet.",
        "000000", "F7F7FF", "00FFFF", "FF8800", "FFFF00", "E780E7", "FF108C", "00F794",
    ),
    DisplayPalette(
        "solar-dark", "Solar Dark", "Muted solar colors for long monitoring sessions with reduced glare.",
        "294E4A", "FFFFFF", "84CAF7", "FFE3BD", "FFF7C6", "D6BDD6", "FFB1BD", "94FB94",
    ),
    DisplayPalette(
        "solar-light", "Solar Light", "Warm paper background with restrained, saturated hierarchy colors.",
        "FFF7D6", "294E4A", "000084", "840000", "526B29", "4A007B", "AD2121", "006300",
    ),
    DisplayPalette(
        "monochrome-ice", "Monochrome Ice", "Calm pale blues and lavender on deep navy with a distinct alert pink.",
        "18186B", "FFFFFF", "ADD6DE", "84CAF7", "DEFFFF", "D6BDD6", "EF7F7B", "39DECE",
    ),
    DisplayPalette(
        "purple-dusk", "Purple Dusk", "Soft dusk pastels on deep violet for an expressive but readable display.",
        "4A007B", "FFFFFF", "ADD6DE", "FF9C73", "FFFF00", "D6BDD6", "FFB1BD", "7BFFCE",
    ),
    DisplayPalette(
        "slate-professional", "Slate Professional", "Conservative slate background with crisp operational accents.",
        "294E4A", "FFFFFF", "84CAE7", "FFE3BD", "FFFFDE", "D6BDD6", "FFB1BD", "8CEB8C",
    ),
)


def palette_by_id(palette_id: str) -> Optional[DisplayPalette]:
    return next((palette for palette in PALETTES if palette.id == palette_id), None)


def item_key(name: str, option: Optional[str]) -> str:
    return name


def option_choices(name: str, screen_name: Optional[str] = None, default: Optional[str] = None) -> Tuple[str, ...]:
    if name.startswith("Icon"):
        return ICON_OPTION_CHOICES
    if name in ("System option", "Department option", "Channel option"):
        return HUGE_OPTION_CHOICES
    if name.startswith("Option A") or name.startswith("Option B") or name.startswith("Option C"):
        return LARGE_OPTION_CHOICES
    if name.startswith("Option_"):
        return SMALL_OPTION_CHOICES
    return ()


def _build_layout_template(
    template_id: str,
    name: str,
    description: str,
    scenario: str,
    *,
    small: Tuple[str, ...],
    simple_large: Tuple[str, ...],
    detail_large: Tuple[str, ...],
    special_large: Tuple[str, ...],
    icons: Tuple[str, ...],
    system_option: str,
) -> DisplayLayoutTemplate:
    overrides: Dict[str, str] = {}
    small_by_name = dict(zip((f"Option_{index}" for index in range(1, 9)), small))
    for screen_name, items in SCREEN_SPECS.items():
        large = simple_large if screen_name.startswith("Simple") else detail_large if screen_name.startswith("Detail") else special_large
        large_index = icon_index = 0
        for index, (item_name, default) in enumerate(items):
            selected: Optional[str] = None
            if item_name.startswith("Option_"):
                selected = small_by_name[item_name]
            elif item_name in ("System option", "Department option", "Channel option"):
                if item_name == "System option":
                    selected = system_option
                elif item_name == "Department option":
                    selected = "SiteName" if "Trunk" in screen_name else "NumberTag"
                else:
                    selected = "TGID" if "Trunk" in screen_name else "Frequency"
            elif item_name.startswith("Option A") or item_name.startswith("Option B") or item_name.startswith("Option C"):
                selected = large[large_index]
                large_index += 1
            elif item_name.startswith("Icon"):
                selected = icons[icon_index]
                icon_index += 1
            if selected is not None and selected != default:
                overrides[f"{screen_name}||{index}"] = selected
    for screen_name, items in SCREEN_SPECS.items():
        used = set()
        data_indices = [
            index for index, (item_name, _) in enumerate(items)
            if item_name in ("System option", "Department option", "Channel option")
        ]
        data_indices.extend(
            index for index, (item_name, _) in enumerate(items)
            if item_name.startswith(("Option A", "Option B", "Option C"))
        )
        for index in data_indices:
            item_name, default = items[index]
            key = f"{screen_name}||{index}"
            selected = overrides.get(key, default)
            if selected in (None, "Empty"):
                continue
            if selected in used:
                choices = option_choices(item_name, screen_name, default)
                selected = next(choice for choice in DATA_DEDUP_FALLBACKS if choice in choices and choice not in used)
                if selected == default:
                    overrides.pop(key, None)
                else:
                    overrides[key] = selected
            used.add(selected)
        non_icon_options = {
            overrides.get(f"{screen_name}||{index}", default)
            for index, (item_name, default) in enumerate(items)
            if not item_name.startswith("Icon") and option_choices(item_name, screen_name, default)
        }
        icon_used = set()
        for index, (item_name, default) in enumerate(items):
            if not item_name.startswith("Icon"):
                continue
            key = f"{screen_name}||{index}"
            selected = overrides.get(key, default)
            if selected in non_icon_options or selected in icon_used:
                replacement = next((
                    choice for choice in ICON_OPTION_CHOICES
                    if choice != "Empty" and choice not in non_icon_options and choice not in icon_used
                ), None)
                if replacement is not None:
                    selected = replacement
                    if selected == default:
                        overrides.pop(key, None)
                    else:
                        overrides[key] = selected
            if selected not in (None, "Empty"):
                icon_used.add(selected)
    return DisplayLayoutTemplate(template_id, name, description, scenario, overrides)


LAYOUT_TEMPLATES: Tuple[DisplayLayoutTemplate, ...] = (
    DisplayLayoutTemplate(
        "sentinel-export", "Sentinel Export", "Preserves the attached Sentinel export exactly.",
        "Balanced starting point with familiar defaults and intentional empty slots.", {},
    ),
    _build_layout_template(
        "dispatch", "Dispatch Essentials", "Prioritizes dispatch identity, frequency/TGID, service, tone, and signal details.",
        "Everyday public-safety monitoring and fast channel identification.",
        small=("ATT", "Bluetooth", "Day", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("ServiceType", "CTCSS/DCS"),
        detail_large=("Volume&Squelch", "NumberTag", "ServiceType", "CTCSS/DCS", "SystemId", "Frequency", "SysSubID", "SiteId", "WACN", "BattVoltage", "UnitId", "Rssi"),
        special_large=("Volume&Squelch", "NumberTag", "Frequency", "BattVoltage", "ServiceType", "Rssi", "TGID", "Rssi Bar"),
        icons=("Modulation", "P_Ch", "IFX", "LVL", "Bluetooth", "REC", "GPS", "PRI", "CC", "WxPRI"),
        system_option="FL_Name",
    ),
    _build_layout_template(
        "technical", "Technical Diagnostics", "Surfaces decoding, RF, network, filter, and error diagnostics.",
        "Troubleshooting reception, simulcast, digital decoding, and trunking behavior.",
        small=("ATT", "Bluetooth", "Day", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("Frequency", "D_ErrorCount"),
        detail_large=("Volume&Squelch", "NumberTag", "D_ErrorCount", "Noise", "Filter", "Frequency", "SystemId", "SysSubID", "WACN", "Rssi", "Rssi Bar", "BattVoltage"),
        special_large=("Volume&Squelch", "NumberTag", "D_ErrorCount", "Noise", "Filter", "Frequency", "Rssi", "Rssi Bar"),
        icons=("Modulation", "P_Ch", "IFX", "LVL", "Bluetooth", "REC", "GPS", "PRI", "SCR", "REP"),
        system_option="SystemId",
    ),
    _build_layout_template(
        "mobile-gps", "Mobile & GPS", "Emphasizes location, site, navigation, signal, and power information.",
        "Vehicle use, location control, roaming, and identifying the active site.",
        small=("ATT", "Bluetooth", "GPS", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("SiteName", "Frequency"),
        detail_large=("Volume&Squelch", "NumberTag", "latitude", "longitude", "SiteName", "SiteId", "Frequency", "Rssi", "Filter", "BattVoltage", "USB2_vbus", "UnitId"),
        special_large=("Volume&Squelch", "NumberTag", "latitude", "longitude", "SiteName", "SiteId", "Rssi", "BattVoltage"),
        icons=("GPS", "Bluetooth", "Modulation", "P_Ch", "IFX", "LVL", "REC", "PRI", "CC", "WxPRI"),
        system_option="FL_Name",
    ),
    _build_layout_template(
        "unit-identification", "Unit Identification", "Maximizes unit, talkgroup, system, site, and service identity fields.",
        "Following individual radios and identifying unknown unit activity.",
        small=("ATT", "Bluetooth", "Day", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("UnitIdName", "UnitId"),
        detail_large=("Volume&Squelch", "NumberTag", "UnitId", "UnitIdName", "UnitIdName_1", "UnitIdName_2", "UnitIdName_3", "UnitIdName_4", "TGID", "SystemId", "SiteId", "Rssi"),
        special_large=("Volume&Squelch", "NumberTag", "UnitId", "UnitIdName", "TGID", "SystemId", "SiteId", "Rssi"),
        icons=("Modulation", "P_Ch", "Bluetooth", "LVL", "IFX", "REC", "GPS", "PRI", "CC", "WxPRI"),
        system_option="SystemId",
    ),
    _build_layout_template(
        "sds150-telemetry", "SDS150 Telemetry", "Highlights SDS150 battery, temperature, USB power, filtering, and RF health.",
        "Bench testing, power diagnostics, and monitoring receiver health.",
        small=("ATT", "Bluetooth", "Day", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("Battery Current", "BattVoltage"),
        detail_large=("Volume&Squelch", "NumberTag", "Battery Current", "Battery Temperature", "BattVoltage", "USB2_vbus", "Filter", "Noise", "D_ErrorCount", "Rssi", "Rssi Bar", "Frequency"),
        special_large=("Volume&Squelch", "NumberTag", "Battery Current", "Battery Temperature", "BattVoltage", "USB2_vbus", "Rssi", "Rssi Bar"),
        icons=("Bluetooth", "Modulation", "P_Ch", "IFX", "LVL", "REC", "GPS", "PRI", "CC", "WxPRI"),
        system_option="SystemType",
    ),
    _build_layout_template(
        "discovery", "Discovery & Close Call", "Emphasizes unknown-signal identification, capture, and RF quality.",
        "Close Call, limit/custom search, repeater finding, and identifying new activity.",
        small=("ATT", "Bluetooth", "SCR", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("Frequency", "CTCSS/DCS"),
        detail_large=("Volume&Squelch", "NumberTag", "Frequency", "CTCSS/DCS", "SystemType", "SystemId", "TGID", "UnitId", "D_ErrorCount", "Noise", "Rssi", "Rssi Bar"),
        special_large=("Volume&Squelch", "NumberTag", "Frequency", "CTCSS/DCS", "SystemId", "UnitId", "Rssi", "Rssi Bar"),
        icons=("SCR", "REP", "IFX", "LVL", "Bluetooth", "REC", "GPS", "PRI", "CC", "WxPRI"),
        system_option="SystemType",
    ),
    _build_layout_template(
        "trunk-network", "Trunk Network Analysis", "Surfaces P25 network, site, talkgroup, unit, and decoding context.",
        "Analyzing multi-site trunked systems, roaming, and talkgroup behavior.",
        small=("ATT", "Bluetooth", "Day", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("SystemId", "TGID"),
        detail_large=("Volume&Squelch", "NumberTag", "SystemId", "SysSubID", "WACN", "SiteId", "SiteName", "TGID", "UnitId", "UnitIdName", "D_ErrorCount", "Rssi"),
        special_large=("Volume&Squelch", "NumberTag", "SystemId", "SysSubID", "WACN", "SiteId", "TGID", "Rssi"),
        icons=("Modulation", "P_Ch", "IFX", "LVL", "Bluetooth", "REC", "GPS", "PRI", "CC", "WxPRI"),
        system_option="SystemId",
    ),
    _build_layout_template(
        "aviation-marine", "Aviation & Marine", "Prioritizes frequency, modulation, service, location, and signal strength.",
        "Civil/military aviation, marine traffic, rail, and conventional channel monitoring.",
        small=("ATT", "Day", "GPS", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("Frequency", "ServiceType"),
        detail_large=("Volume&Squelch", "NumberTag", "Frequency", "ServiceType", "CTCSS/DCS", "latitude", "longitude", "SiteName", "Filter", "Noise", "Rssi", "Rssi Bar"),
        special_large=("Volume&Squelch", "NumberTag", "Frequency", "ServiceType", "latitude", "longitude", "Rssi", "Rssi Bar"),
        icons=("Modulation", "Bluetooth", "GPS", "IFX", "LVL", "REC", "P_Ch", "PRI", "CC", "WxPRI"),
        system_option="FL_Name",
    ),
    _build_layout_template(
        "recording-alerts", "Recording & Alerts", "Makes recording, priority, Close Call, weather, and active-state indicators prominent.",
        "Event monitoring, unattended recording, and rapid attention to priority activity.",
        small=("ATT", "Day", "REC", "Time", "Volume", "Squelch", "P25Status", "TdmaSlot"),
        simple_large=("ServiceType", "Frequency"),
        detail_large=("Volume&Squelch", "NumberTag", "ServiceType", "Frequency", "TGID", "UnitId", "UnitIdName", "SystemId", "BattVoltage", "Rssi", "Rssi Bar", "D_ErrorCount"),
        special_large=("Volume&Squelch", "NumberTag", "ServiceType", "Frequency", "TGID", "UnitId", "Rssi", "Rssi Bar"),
        icons=("REC", "PRI", "CC", "WxPRI", "Bluetooth", "GPS", "Modulation", "P_Ch", "SCR", "REP"),
        system_option="FL_Name",
    ),
)


def layout_template_by_id(template_id: str) -> Optional[DisplayLayoutTemplate]:
    return next((template for template in LAYOUT_TEMPLATES if template.id == template_id), None)


def layout_template_catalog() -> List[dict]:
    return [
        {
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "scenario": template.scenario,
            "screen_item_options": dict(template.screen_item_options),
        }
        for template in LAYOUT_TEMPLATES
    ]


def _category(name: str, option: Optional[str]) -> str:
    combined = f"{name} {option or ''}".casefold()
    if name == "Avoid" or name == "Hold" or option in ("CC", "WxPRI") or "close call" in combined:
        return "alert"
    if option in ("FL_Name", "SystemType", "SystemId", "SysSubID", "WACN"):
        return "system"
    if option in ("SiteName", "SiteId", "Lcn", "latitude", "longitude"):
        return "department"
    if option in (
        "Frequency", "TGID", "CTCSS/DCS", "ServiceType", "TdmaSlot", "UnitId",
        "UnitIdName", "UnitIdName_1", "UnitIdName_2", "UnitIdName_3", "UnitIdName_4",
    ):
        return "channel"
    if option in ("ATT", "Bluetooth", "SCR", "GPS", "IFX", "Modulation", "P_Ch", "PRI", "REC", "REP", "LVL"):
        return "accent"
    if option in (
        "Battery Current", "Battery Temperature", "BattVoltage", "D_ErrorCount",
        "Filter", "Noise", "Rssi", "Rssi Bar", "USB2_vbus",
    ):
        return "metadata"
    if name in ("System Name", "System option", "Primary Area-1"):
        return "system"
    if name in ("Department Name", "Department option", "Primary Area-2"):
        return "department"
    if name in ("Channel Name", "Channel option", "Primary Area-3"):
        return "channel"
    if name in ("Sub Info", "Modulation", "Detail Info"):
        return "channel"
    if name.startswith("Option A") or name.startswith("Option B"):
        return "metadata"
    if name.startswith("Icon") and option not in (None, "Empty"):
        return "accent"
    return "status"


def _row_category_overrides(row_categories: Dict[str, Tuple[str, ...]]) -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    for screen_name, rows in display_layout_catalog().items():
        counters: Dict[str, int] = {}
        for row in rows:
            choices = row_categories.get(row["class_name"])
            if not choices:
                continue
            occurrence = counters.get(row["class_name"], 0)
            category = choices[occurrence % len(choices)]
            counters[row["class_name"]] = occurrence + 1
            for index in row["indices"]:
                overrides[f"{screen_name}||{index}"] = category
    return overrides


def _granular_category_overrides() -> Dict[str, str]:
    overrides: Dict[str, str] = {}
    softkey_categories = {"Soft1 Key": "system", "Soft2 Key": "department", "Soft3 Key": "channel"}
    info_categories = {"Info Area 1": "system", "Info Area 2": "department", "Info Area 3": "channel"}
    for screen_name, items in SCREEN_SPECS.items():
        for index, (name, option) in enumerate(items):
            category: Optional[str] = None
            if name in ("SP0", "SP1", "SP2"):
                continue
            if name in softkey_categories:
                category = softkey_categories[name]
            elif name in info_categories:
                category = info_categories[name]
            elif name in ("Func", "key", "Dir"):
                category = "accent"
            elif name in ("SIG", "Option_7", "Option_8"):
                category = "channel"
            elif name == "BATT":
                category = "metadata"
            elif name in ("Option_3", "Option_4", "Option_5", "Option_6", "Option C-1", "Option C-2"):
                category = "metadata"
            if category:
                overrides[f"{screen_name}||{index}"] = category
    return overrides


def _spectrum_role_slots() -> Dict[str, int]:
    slots: Dict[str, int] = {}
    for screen_name, items in SCREEN_SPECS.items():
        large_slot = 12
        for index, (name, option) in enumerate(items):
            slot: Optional[int] = None
            if name in ("SP0", "SP1", "SP2") or option == "Empty":
                continue
            if name == "Func": slot = 0
            elif name in ("Option_1", "Option_2"): slot = 1
            elif name in ("Option_3", "Option_4"): slot = 2
            elif name == "SIG": slot = 3
            elif name == "BATT": slot = 4
            elif name in ("Option_5", "Option_6", "Option C-1", "Option C-2"): slot = 5
            elif name in ("Option_7", "Option_8"): slot = 6
            elif name in ("key", "Dir"): slot = 7
            elif name in ("System Name", "System option", "Primary Area-1", "Info Area 1", "Soft1 Key"): slot = 8
            elif name in ("Department Name", "Department option", "Primary Area-2", "Info Area 2", "Soft2 Key"): slot = 9
            elif name in ("Channel Name", "Channel option", "Primary Area-3", "Info Area 3", "Soft3 Key"): slot = 10
            elif name in ("Avoid", "Hold"): slot = 11
            elif name.startswith(("Option A", "Option B")):
                slot = large_slot
                large_slot = 12 + ((large_slot - 11) % 4)
            elif name in ("Sub Info", "Modulation", "Detail Info"): slot = 16
            elif name.startswith("Icon"):
                slot = 17
            if slot is not None:
                slots[f"{screen_name}||{index}"] = slot
    return slots


def _spectrum_row_slots() -> Dict[str, int]:
    slots: Dict[str, int] = {}
    for screen_name, rows in display_layout_catalog().items():
        for row_index, row in enumerate(rows):
            for index in row["indices"]:
                name, option = SCREEN_SPECS[screen_name][index]
                if name not in ("SP0", "SP1", "SP2") and option != "Empty":
                    slots[f"{screen_name}||{index}"] = row_index % 18
    return slots


def _spectrum_matrix_slots() -> Dict[str, int]:
    slots: Dict[str, int] = {}
    for screen_name, items in SCREEN_SPECS.items():
        visible_index = 0
        for index, (name, option) in enumerate(items):
            if name in ("SP0", "SP1", "SP2") or option == "Empty":
                continue
            slots[f"{screen_name}||{index}"] = visible_index % 18
            visible_index += 1
    return slots


def _stable_item_slots() -> Dict[str, int]:
    slots: Dict[str, int] = {}
    fixed_slots = {
        "Func": 0, "SIG": 5, "BATT": 6, "key": 9, "Dir": 9,
        "System Name": 10, "System option": 10,
        "Department Name": 13, "Department option": 13,
        "Channel Name": 15, "Channel option": 15,
        "Avoid": 22, "Hold": 22,
        "Info Area 1": 25, "Primary Area-1": 25,
        "Info Area 2": 26, "Primary Area-2": 26,
        "Info Area 3": 27, "Primary Area-3": 27,
        "Soft1 Key": 25, "Soft2 Key": 26, "Soft3 Key": 27,
    }
    for screen_name, items in SCREEN_SPECS.items():
        for index, (name, _) in enumerate(items):
            if name in ("SP0", "SP1", "SP2"):
                continue
            if name.startswith("Icon"):
                slot = 28
            elif name.startswith(("Option A", "Option B")):
                slot = 29
            elif name in ("Option_3", "Option_4"):
                slot = 4
            elif name in ("Option_5", "Option_6", "Option C-1", "Option C-2"):
                slot = 7
            elif name in ("Option_7", "Option_8"):
                slot = 8
            else:
                slot = fixed_slots.get(name, 29)
            slots[f"{screen_name}||{index}"] = slot
    return slots


def _stable_option_slots() -> Dict[str, int]:
    groups = {
        1: ("ATT",), 2: ("Bluetooth",), 3: ("GPS",), 4: ("Day", "Time"),
        5: ("Rssi", "Rssi Bar"),
        6: ("BATT", "Battery Current", "Battery Temperature", "BattVoltage", "USB2_vbus"),
        7: ("Volume", "Squelch", "Volume&Squelch"),
        8: ("P25Status",), 10: ("FL_Name",),
        11: ("SystemType", "SystemId"), 12: ("SysSubID", "WACN"),
        14: ("SiteName", "SiteId", "Lcn", "latitude", "longitude"),
        16: ("Frequency",), 17: ("TGID",), 18: ("ServiceType",),
        19: ("CTCSS/DCS", "Modulation", "TdmaSlot"),
        20: ("UnitId", "UnitIdName", "UnitIdName_1", "UnitIdName_2", "UnitIdName_3", "UnitIdName_4"),
        21: ("Filter", "Noise", "D_ErrorCount"),
        23: ("REC", "PRI", "P_Ch"), 24: ("CC", "WxPRI", "SCR", "REP"),
        28: ("IFX", "LVL"), 29: ("NumberTag",),
    }
    return {option: slot for slot, options in groups.items() for option in options}


def palette_spectrum(palette: DisplayPalette, count: int = 30) -> List[str]:
    background = palette.background
    contrast_candidates = [
        value for _, value in SUPPORTED_DISPLAY_COLORS
        if value != background and contrast_ratio(value, background) >= 4.5
    ]

    def hls(value: str) -> Tuple[float, float, float]:
        red, green, blue = (int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))
        return colorsys.rgb_to_hls(red, green, blue)

    dark_background = _relative_luminance(background) < 0.35
    colorful = [
        value for value in contrast_candidates
        if hls(value)[2] >= 0.22
        and ((hls(value)[1] <= 0.9) if dark_background else (hls(value)[1] >= 0.1))
    ]
    candidates = colorful if len(colorful) >= count else contrast_candidates
    selected = []
    for category, value in palette.colors().items():
        if category not in ("background", "status") and value in candidates and value not in selected:
            selected.append(value)

    def coordinates(value: str) -> Tuple[float, float, float]:
        red, green, blue = (int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))
        hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
        return hue, lightness, saturation

    points = {value: coordinates(value) for value in candidates}

    def distance(first: str, second: str) -> float:
        hue_a, light_a, saturation_a = points[first]
        hue_b, light_b, saturation_b = points[second]
        hue = min(abs(hue_a - hue_b), 1 - abs(hue_a - hue_b)) * 2
        return (hue ** 2 + ((light_a - light_b) * 1.5) ** 2 + ((saturation_a - saturation_b) * 0.55) ** 2) ** 0.5

    while len(selected) < count:
        remaining = [value for value in candidates if value not in selected]
        selected.append(max(
            remaining,
            key=lambda value: (
                min(distance(value, existing) for existing in selected),
                points[value][2],
                contrast_ratio(value, background),
            ),
        ))
    return selected[:count]


COLOR_GROUPINGS: Tuple[DisplayColorGrouping, ...] = (
    DisplayColorGrouping(
        "balanced", "Balanced Semantic", "Uses the logical color of each selected data type.",
        "Basic", {}, {},
    ),
    DisplayColorGrouping(
        "basic", "Basic Hierarchy", "Keeps system, department, channel, and alerts distinct while simplifying secondary data.",
        "Basic", {"metadata": "status", "accent": "status"}, {},
    ),
    DisplayColorGrouping(
        "full-spectrum", "Full Spectrum Granular", "Colors hierarchy, controls, time, signal, power, info areas, icons, and soft keys in granular related groups.",
        "Colorful", {}, _granular_category_overrides(), _spectrum_role_slots(),
    ),
    DisplayColorGrouping(
        "maximum-spectrum-rows", "Maximum Spectrum Rows", "Uses a distinct high-contrast theme color for each physical row while preserving row relationships.",
        "Colorful", {}, {}, _spectrum_row_slots(),
    ),
    DisplayColorGrouping(
        "rainbow-matrix", "Rainbow Data Matrix", "Cycles the full 18-color theme spectrum across visible fields for maximum visual separation.",
        "Colorful", {}, {}, _spectrum_matrix_slots(),
    ),
    DisplayColorGrouping(
        "stable-item-rainbow", "Stable Item Rainbow", "Keeps each data meaning the same color across all screens and templates while different meanings use different spectrum colors.",
        "Colorful", {}, {}, _stable_item_slots(), _stable_option_slots(),
    ),
    DisplayColorGrouping(
        "row-bands", "Colorful Row Bands", "Assigns distinct theme colors to top, utility, hierarchy, detail, icon, and bottom rows.",
        "Colorful", {}, _row_category_overrides({
            "scanner-status-row": ("accent",), "scanner-utility-row": ("metadata",),
            "scanner-info-top": ("system",), "scanner-info-pair": ("department", "channel"),
            "scanner-hierarchy-row": ("system", "department", "channel"),
            "scanner-special-row": ("system", "department"), "scanner-special-detail": ("channel",),
            "scanner-detail-pair": ("metadata", "accent"), "scanner-icons": ("accent",),
            "scanner-softkeys": ("alert",),
        }),
    ),
    DisplayColorGrouping(
        "top-bottom", "Top & Bottom Contrast", "Uses one strong group for the top rows and another for icons and soft keys while preserving the center hierarchy.",
        "Rows", {}, _row_category_overrides({
            "scanner-status-row": ("system",), "scanner-utility-row": ("department",),
            "scanner-info-top": ("system",), "scanner-info-pair": ("metadata",),
            "scanner-icons": ("accent",), "scanner-softkeys": ("channel",),
        }),
    ),
    DisplayColorGrouping(
        "alternating", "Alternating Data Rows", "Alternates related detail rows for fast horizontal scanning.",
        "Rows", {}, _row_category_overrides({
            "scanner-status-row": ("accent",), "scanner-utility-row": ("metadata",),
            "scanner-info-top": ("system",), "scanner-info-pair": ("department", "channel"),
            "scanner-hierarchy-row": ("system", "department", "channel"),
            "scanner-special-row": ("system", "department"), "scanner-special-detail": ("channel",),
            "scanner-detail-pair": ("metadata", "accent", "system", "department", "channel"),
            "scanner-icons": ("accent",), "scanner-softkeys": ("metadata",),
        }),
    ),
    DisplayColorGrouping(
        "technical-emphasis", "Technical Heatmap", "Promotes diagnostics and alerts while muting routine status fields.",
        "Scenario", {"status": "metadata", "metadata": "alert", "accent": "channel"}, {},
    ),
    DisplayColorGrouping(
        "activity-alerts", "Activity & Alerts", "Makes active indicators, recordings, warnings, and alert states dominant.",
        "Scenario", {"status": "metadata", "system": "status", "department": "status", "channel": "accent", "metadata": "channel"}, {},
    ),
    DisplayColorGrouping(
        "hierarchy-focus", "Hierarchy Focus", "Emphasizes system, department, and channel identity with restrained operational details.",
        "Scenario", {"status": "metadata", "accent": "metadata"}, {},
    ),
    DisplayColorGrouping(
        "monochrome", "Uniform Minimal", "Uses one theme foreground for everything except alerts.",
        "Accessibility", {"system": "status", "department": "status", "channel": "status", "metadata": "status", "accent": "status"}, {},
    ),
)


def color_grouping_by_id(grouping_id: str) -> Optional[DisplayColorGrouping]:
    return next((grouping for grouping in COLOR_GROUPINGS if grouping.id == grouping_id), None)


def color_grouping_catalog() -> List[dict]:
    return [
        {
            "id": grouping.id,
            "name": grouping.name,
            "description": grouping.description,
            "style": grouping.style,
            "category_map": dict(grouping.category_map),
            "item_categories": dict(grouping.item_categories),
            "item_color_slots": dict(grouping.item_color_slots or {}),
            "option_color_slots": dict(grouping.option_color_slots or {}),
        }
        for grouping in COLOR_GROUPINGS
    ]


def grouped_category(
    grouping: DisplayColorGrouping,
    screen_name: str,
    index: int,
    name: str,
    option: Optional[str],
) -> str:
    item_category = grouping.item_categories.get(f"{screen_name}||{index}")
    if item_category:
        return item_category
    category = _category(name, option)
    return grouping.category_map.get(category, category)


def generate_display_xml(
    palette: DisplayPalette,
    *,
    color_grouping_id: str = "balanced",
    spectrum_colors: Optional[List[str]] = None,
    global_item_colors: Optional[Dict[str, dict]] = None,
    screen_item_colors: Optional[Dict[str, dict]] = None,
    global_item_options: Optional[Dict[str, str]] = None,
    screen_item_options: Optional[Dict[str, str]] = None,
) -> bytes:
    root = ET.Element("UndienScanner", {"Model": "SDS100", "FileType": "DisplayCustomizer"})
    colors = palette.colors()
    grouping = color_grouping_by_id(color_grouping_id)
    if grouping is None:
        raise ValueError(f"unknown display color grouping: {color_grouping_id}")
    spectrum = [str(color).removeprefix("#").upper() for color in (spectrum_colors or [])]
    if any(color not in SUPPORTED_DISPLAY_COLOR_VALUES for color in spectrum):
        raise ValueError("display spectrum contains an unsupported Sentinel color")
    spectrum.extend(color for color in palette_spectrum(palette) if color not in spectrum)
    if len(spectrum) < 30:
        raise ValueError("display spectrum must resolve to at least 30 Sentinel-supported colors")
    global_item_colors = global_item_colors or {}
    screen_item_colors = screen_item_colors or {}
    global_item_options = global_item_options or {}
    screen_item_options = screen_item_options or {}
    for screen_name, items in SCREEN_SPECS.items():
        screen = ET.SubElement(root, "Screen", {"Name": screen_name})
        for index, (name, option) in enumerate(items):
            override = dict(global_item_colors.get(item_key(name, option)) or {})
            override.update(screen_item_colors.get(f"{screen_name}||{index}") or {})
            choices = option_choices(name, screen_name, option)
            selected_option = option
            global_option = global_item_options.get(item_key(name, option))
            if global_option in choices:
                selected_option = global_option
            screen_option = screen_item_options.get(f"{screen_name}||{index}")
            if screen_option in choices:
                selected_option = screen_option
            category = grouped_category(grouping, screen_name, index, name, selected_option)
            spectrum_slot = (grouping.option_color_slots or {}).get(selected_option)
            if spectrum_slot is None:
                spectrum_slot = (grouping.item_color_slots or {}).get(f"{screen_name}||{index}")
            grouped_text = spectrum[spectrum_slot % len(spectrum)] if spectrum_slot is not None else colors[category]
            attributes = {
                "Name": name,
                "Text": str(override.get("text") or grouped_text).upper(),
                "Back": str(override.get("back") or palette.background).upper(),
            }
            if selected_option is not None:
                attributes["Option"] = selected_option
            ET.SubElement(screen, "Item", attributes)
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def display_item_catalog() -> Dict[str, List[dict]]:
    catalog = {
        screen_name: [
            {
                "index": index,
                "name": name,
                "option": option,
                "item_key": item_key(name, option),
                "category": _category(name, option),
                "screen_key": f"{screen_name}||{index}",
                "option_choices": list(option_choices(name, screen_name, option)),
                "option_categories": {
                    choice: _category(name, choice)
                    for choice in option_choices(name, screen_name, option)
                },
            }
            for index, (name, option) in enumerate(items)
        ]
        for screen_name, items in SCREEN_SPECS.items()
    }
    grouped: Dict[str, List[set]] = {}
    for items in catalog.values():
        for item in items:
            if item["option_choices"]:
                grouped.setdefault(item["item_key"], []).append(set(item["option_choices"]))
    synchronized = {
        key: sorted(set.intersection(*choices)) if choices else []
        for key, choices in grouped.items()
    }
    for items in catalog.values():
        for item in items:
            item["sync_option_choices"] = synchronized.get(item["item_key"], [])
    return catalog


def custom_palette_from_dict(data: dict) -> DisplayPalette:
    if not isinstance(data, dict):
        raise ValueError("custom palette payload must be an object")
    colors = dict(data.get("colors") or {})
    missing = [key for key in COLOR_KEYS if key not in colors]
    if missing:
        raise ValueError(f"missing custom palette colors: {missing}")
    for key in COLOR_KEYS:
        value = str(colors[key]).removeprefix("#").upper()
        if value not in SUPPORTED_DISPLAY_COLOR_VALUES:
            raise ValueError(f"{key}: color #{value} is not supported by Sentinel")
        colors[key] = value
    return DisplayPalette(
        id="custom",
        name=str(data.get("name") or "Custom Palette")[:80],
        description=str(data.get("description") or "User-customized display palette")[:240],
        **colors,
    )


def validate_color_overrides(overrides: dict, valid_keys: set) -> List[str]:
    issues: List[str] = []
    if not isinstance(overrides, dict):
        return ["color overrides must be an object"]
    for key, value in overrides.items():
        if key not in valid_keys:
            issues.append(f"unknown item override key: {key}")
            continue
        if not isinstance(value, dict):
            issues.append(f"{key}: override must be an object")
            continue
        for field in ("text", "back"):
            if field in value and str(value[field]).removeprefix("#").upper() not in SUPPORTED_DISPLAY_COLOR_VALUES:
                issues.append(f"{key}: unsupported {field} color")
    return issues


def generate_custom_display_xml(data: dict) -> Tuple[bytes, List[str]]:
    palette = custom_palette_from_dict(data)
    template_id = str(data.get("layout_template_id") or "sentinel-export")
    template = layout_template_by_id(template_id)
    if template is None:
        raise ValueError(f"unknown display layout template: {template_id}")
    color_grouping_id = str(data.get("color_grouping_id") or "balanced")
    if color_grouping_by_id(color_grouping_id) is None:
        raise ValueError(f"unknown display color grouping: {color_grouping_id}")
    raw_spectrum = data.get("spectrum_colors")
    if raw_spectrum is None:
        spectrum_colors = palette_spectrum(palette)
    elif not isinstance(raw_spectrum, list):
        raise ValueError("display spectrum must be a list")
    else:
        spectrum_colors = [str(color).removeprefix("#").upper() for color in raw_spectrum]
    if len(spectrum_colors) < 18 or any(color not in SUPPORTED_DISPLAY_COLOR_VALUES for color in spectrum_colors):
        raise ValueError("display spectrum must contain at least 18 Sentinel-supported colors")
    global_overrides = dict(data.get("global_item_colors") or {})
    screen_overrides = dict(data.get("screen_item_colors") or {})
    global_options = dict(data.get("global_item_options") or {})
    screen_options = dict(data.get("screen_item_options") or {})
    catalog = display_item_catalog()
    global_keys = {item["item_key"] for items in catalog.values() for item in items}
    screen_keys = {item["screen_key"] for items in catalog.values() for item in items}
    issues = validate_color_overrides(global_overrides, global_keys)
    issues.extend(validate_color_overrides(screen_overrides, screen_keys))
    if issues:
        raise ValueError("; ".join(issues))
    by_global_key = {item["item_key"]: item for items in catalog.values() for item in items if item["sync_option_choices"]}
    by_screen_key = {item["screen_key"]: item for items in catalog.values() for item in items}
    for key, selected in template.screen_item_options.items():
        item = by_screen_key[key]
        if key not in screen_options and item["item_key"] not in global_options:
            screen_options[key] = selected
    for key, selected in global_options.items():
        item = by_global_key.get(key)
        if item is None or selected not in item["sync_option_choices"]:
            raise ValueError(f"{key}: unsupported synchronized display option {selected!r}")
    for key, selected in screen_options.items():
        item = by_screen_key.get(key)
        if item is None or selected not in item["option_choices"]:
            raise ValueError(f"{key}: unsupported display option {selected!r}")
    for mapping in (global_overrides, screen_overrides):
        for value in mapping.values():
            for field in ("text", "back"):
                if field in value:
                    value[field] = str(value[field]).removeprefix("#").upper()
    xml = generate_display_xml(
        palette,
        color_grouping_id=color_grouping_id,
        spectrum_colors=spectrum_colors,
        global_item_colors=global_overrides,
        screen_item_colors=screen_overrides,
        global_item_options=global_options,
        screen_item_options=screen_options,
    )
    contrast_warnings: List[str] = []
    root = ET.fromstring(xml)
    for screen in root.findall("Screen"):
        for index, item in enumerate(screen.findall("Item")):
            ratio = contrast_ratio(item.attrib["Text"], item.attrib["Back"])
            if ratio < 4.5:
                contrast_warnings.append(
                    f"{screen.attrib['Name']} item {index} ({item.attrib.get('Name')}): {ratio:.2f}:1"
                )
    return xml, contrast_warnings


def _relative_luminance(color: str) -> float:
    values = [int(color[index:index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in values]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    high, low = sorted((_relative_luminance(first), _relative_luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def palette_summary(palette: DisplayPalette) -> dict:
    ratios = {
        category: round(contrast_ratio(color, palette.background), 2)
        for category, color in palette.colors().items()
        if category != "background"
    }
    return {
        "id": palette.id,
        "name": palette.name,
        "description": palette.description,
        "colors": palette.colors(),
        "spectrum_colors": palette_spectrum(palette),
        "contrast_ratios": ratios,
        "minimum_contrast": min(ratios.values()),
    }


def validate_palette(palette: DisplayPalette, minimum_ratio: float = 4.5) -> List[str]:
    issues = []
    for category, color in palette.colors().items():
        if color not in SUPPORTED_DISPLAY_COLOR_VALUES:
            issues.append(f"{category}: unsupported Sentinel color {color!r}")
        if category != "background" and contrast_ratio(color, palette.background) < minimum_ratio:
            issues.append(f"{category}: contrast is below {minimum_ratio}:1")
    return issues


def validate_display_xml(data: bytes) -> List[str]:
    issues: List[str] = []
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        return [f"invalid XML: {exc}"]
    if root.tag != "UndienScanner" or root.attrib.get("Model") != "SDS100" or root.attrib.get("FileType") != "DisplayCustomizer":
        issues.append("root attributes do not match Sentinel DisplayCustomizer format")
    screens = {screen.attrib.get("Name"): screen for screen in root.findall("Screen")}
    if set(screens) != set(SCREEN_SPECS):
        issues.append("screen set does not match the seven Sentinel display modes")
    for screen_name, expected in SCREEN_SPECS.items():
        actual = screens.get(screen_name)
        if actual is None:
            continue
        signature = [(item.attrib.get("Name"), item.attrib.get("Option")) for item in actual.findall("Item")]
        if [name for name, _ in signature] != [name for name, _ in expected]:
            issues.append(f"{screen_name}: item names/order differ from the Sentinel template")
        for index, ((name, selected), (_, default)) in enumerate(zip(signature, expected)):
            choices = option_choices(name, screen_name, default)
            if choices and selected not in choices:
                issues.append(f"{screen_name} item {index}: unsupported option {selected!r}")
            elif not choices and selected != default:
                issues.append(f"{screen_name} item {index}: fixed option changed")
        for item in actual.findall("Item"):
            if not all(item.attrib.get(field, "").upper() in SUPPORTED_DISPLAY_COLOR_VALUES for field in ("Text", "Back")):
                issues.append(f"{screen_name}: unsupported Sentinel item color")
                break
    return issues


def supported_color_catalog() -> List[dict]:
    families = (
        ("Neutrals", 0),
        ("Reds", 1),
        ("Oranges", 2),
        ("Yellows", 3),
        ("Yellow-greens", 4),
        ("Greens", 5),
        ("Teals", 6),
        ("Cyans", 7),
        ("Blues", 8),
        ("Violets", 9),
        ("Magentas", 10),
        ("Pinks", 11),
    )

    def color_details(sentinel_index: int, name: str, value: str) -> dict:
        red, green, blue = (int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))
        hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
        degrees = hue * 360
        if saturation < 0.12 or lightness <= 0.08 or lightness >= 0.94:
            family, family_order = families[0]
        elif degrees < 15 or degrees >= 345:
            family, family_order = families[1]
        elif degrees < 45:
            family, family_order = families[2]
        elif degrees < 70:
            family, family_order = families[3]
        elif degrees < 100:
            family, family_order = families[4]
        elif degrees < 155:
            family, family_order = families[5]
        elif degrees < 185:
            family, family_order = families[6]
        elif degrees < 205:
            family, family_order = families[7]
        elif degrees < 255:
            family, family_order = families[8]
        elif degrees < 285:
            family, family_order = families[9]
        elif degrees < 325:
            family, family_order = families[10]
        else:
            family, family_order = families[11]
        return {
            "sentinel_index": sentinel_index,
            "name": name,
            "value": value,
            "family": family,
            "family_order": family_order,
            "hue": round(degrees, 2),
            "lightness": round(lightness, 4),
            "saturation": round(saturation, 4),
        }

    catalog = [
        color_details(index, name, value)
        for index, (name, value) in enumerate(SUPPORTED_DISPLAY_COLORS)
    ]
    catalog.sort(key=lambda color: (
        color["family_order"],
        color["lightness"],
        color["hue"],
        -color["saturation"],
        color["name"],
    ))
    for index, color in enumerate(catalog):
        color["index"] = index
    return catalog
