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

from wasds150.display_colors import (
    SUPPORTED_DISPLAY_COLORS,
    SUPPORTED_DISPLAY_COLOR_VALUES,
)


ItemSpec = Tuple[str, Optional[str]]
COLOR_KEYS = ("background", "status", "system", "department", "channel", "metadata", "alert", "accent")

SMALL_OPTION_CHOICES = (
    "Empty", "ATT", "Bluetooth", "Day", "Time", "P25Status", "TdmaSlot",
    "Volume", "Squelch", "GPS", "IFX", "Modulation", "P_Ch", "PRI",
    "REC", "REP", "CC", "WxPRI", "SCR", "LVL", "BattVoltage", "Rssi",
    "NumberTag",
)
ICON_OPTION_CHOICES = (
    "Empty", "Modulation", "P_Ch", "IFX", "LVL", "REC", "GPS", "PRI",
    "CC", "WxPRI", "SCR", "REP",
)
SYSTEM_OPTION_CHOICES = ("Empty", "FL_Name", "SystemId", "SysSubID", "WACN", "NumberTag")
DEPARTMENT_OPTION_CHOICES = ("Empty", "SiteName")
CHANNEL_OPTION_CHOICES = ("Empty", "Frequency", "TGID")
EXACT_OPTION_CHOICES = {
    "Option_1": ("Empty", "ATT"),
    "Option_2": ("Empty", "Bluetooth"),
    "Option_3": SMALL_OPTION_CHOICES,
    "Option_4": SMALL_OPTION_CHOICES,
    "Option_5": ("Empty", "Volume"),
    "Option_6": ("Empty", "Squelch"),
    "Option_7": ("Empty", "P25Status"),
    "Option_8": ("Empty", "TdmaSlot"),
}


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
    if screen_name in ("Weather", "Tone out"):
        return ()
    if name.startswith("Icon"):
        return ICON_OPTION_CHOICES
    if name == "System option":
        return SYSTEM_OPTION_CHOICES
    if name == "Department option":
        return DEPARTMENT_OPTION_CHOICES
    if name == "Channel option":
        return CHANNEL_OPTION_CHOICES
    if name.startswith("Option A") or name.startswith("Option B") or name.startswith("Option C"):
        return tuple(dict.fromkeys(("Empty", default))) if default is not None else ()
    if name == "Option_7" and default == "Empty":
        return ("Empty",)
    if name == "Option_8" and default == "Empty":
        return ("Empty",)
    if name in EXACT_OPTION_CHOICES:
        return EXACT_OPTION_CHOICES[name]
    return ()


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


def generate_display_xml(
    palette: DisplayPalette,
    *,
    global_item_colors: Optional[Dict[str, dict]] = None,
    screen_item_colors: Optional[Dict[str, dict]] = None,
    global_item_options: Optional[Dict[str, str]] = None,
    screen_item_options: Optional[Dict[str, str]] = None,
) -> bytes:
    root = ET.Element("UndienScanner", {"Model": "SDS100", "FileType": "DisplayCustomizer"})
    colors = palette.colors()
    global_item_colors = global_item_colors or {}
    screen_item_colors = screen_item_colors or {}
    global_item_options = global_item_options or {}
    screen_item_options = screen_item_options or {}
    for screen_name, items in SCREEN_SPECS.items():
        screen = ET.SubElement(root, "Screen", {"Name": screen_name})
        for index, (name, option) in enumerate(items):
            category = _category(name, option)
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
            attributes = {
                "Name": name,
                "Text": str(override.get("text") or colors[category]).upper(),
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
    return [
        {"index": index, "name": name, "value": value}
        for index, (name, value) in enumerate(SUPPORTED_DISPLAY_COLORS)
    ]
