"""SDS100/SDS150 display palette generation and validation.

The XML shape follows an actual Sentinel export (including Uniden's historic
``UndienScanner`` root spelling). Screen/item names and option codes are kept
separate from palette colors so every palette has an identical, predictable
information layout.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


ItemSpec = Tuple[str, Optional[str]]


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


PALETTES: Tuple[DisplayPalette, ...] = (
    DisplayPalette(
        "night-ops", "Night Ops", "Cool hierarchy colors on true black for dark cabins and general use.",
        "000000", "F8FAFC", "38BDF8", "FB923C", "FDE047", "C4B5FD", "FB7185", "4ADE80",
    ),
    DisplayPalette(
        "daylight-high-contrast", "Daylight High Contrast", "Dark saturated labels on white for bright outdoor viewing.",
        "FFFFFF", "111827", "075985", "9A3412", "713F12", "5B21B6", "B91C1C", "166534",
    ),
    DisplayPalette(
        "colorblind-dark", "Colorblind Dark", "Okabe-Ito-inspired blue, orange, yellow, and purple grouping.",
        "0B0F14", "F2F2F2", "56B4E9", "E69F00", "F0E442", "CC79A7", "F25F5C", "009E73",
    ),
    DisplayPalette(
        "low-light-amber", "Low-Light Amber", "Warm amber hierarchy with restrained red accents to preserve night vision.",
        "000000", "FFE8D6", "FF6B35", "FF9F1C", "FFD166", "E6A8D7", "FF4D6D", "C7F9CC",
    ),
)


def palette_by_id(palette_id: str) -> Optional[DisplayPalette]:
    return next((palette for palette in PALETTES if palette.id == palette_id), None)


def _category(name: str, option: Optional[str]) -> str:
    combined = f"{name} {option or ''}".casefold()
    if name == "Avoid" or name == "Hold" or option in ("CC", "WxPRI") or "close call" in combined:
        return "alert"
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


def generate_display_xml(palette: DisplayPalette) -> bytes:
    root = ET.Element("UndienScanner", {"Model": "SDS100", "FileType": "DisplayCustomizer"})
    colors = palette.colors()
    for screen_name, items in SCREEN_SPECS.items():
        screen = ET.SubElement(root, "Screen", {"Name": screen_name})
        for name, option in items:
            category = _category(name, option)
            attributes = {
                "Name": name,
                "Text": colors[category],
                "Back": palette.background,
            }
            if option is not None:
                attributes["Option"] = option
            ET.SubElement(screen, "Item", attributes)
    ET.indent(root, space="    ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


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
        "contrast_ratios": ratios,
        "minimum_contrast": min(ratios.values()),
    }


def validate_palette(palette: DisplayPalette, minimum_ratio: float = 4.5) -> List[str]:
    issues = []
    for category, color in palette.colors().items():
        if not re.fullmatch(r"[0-9A-F]{6}", color):
            issues.append(f"{category}: invalid RGB hex {color!r}")
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
        if signature != expected:
            issues.append(f"{screen_name}: item names/options/order differ from the Sentinel template")
        for item in actual.findall("Item"):
            if not all(re.fullmatch(r"[0-9A-F]{6}", item.attrib.get(field, "")) for field in ("Text", "Back")):
                issues.append(f"{screen_name}: invalid item color")
                break
    return issues
