import xml.etree.ElementTree as ET
from pathlib import Path

from wasds150.display_customizer import (
    PALETTES,
    SCREEN_SPECS,
    generate_custom_display_xml,
    generate_display_xml,
    palette_summary,
    supported_color_catalog,
    validate_display_xml,
    validate_palette,
)
from wasds150.display_colors import SUPPORTED_DISPLAY_COLORS, SUPPORTED_DISPLAY_COLOR_VALUES


def _signature(root):
    return {
        screen.attrib["Name"]: [
            (item.attrib.get("Name"), item.attrib.get("Option"))
            for item in screen.findall("Item")
        ]
        for screen in root.findall("Screen")
    }


def test_all_display_palettes_meet_contrast_and_xml_validation():
    assert len(PALETTES) >= 12
    for palette in PALETTES:
        assert validate_palette(palette) == []
        assert palette_summary(palette)["minimum_contrast"] >= 4.5
        assert validate_display_xml(generate_display_xml(palette)) == []


def test_supported_display_color_table_is_exact_and_unique():
    assert len(SUPPORTED_DISPLAY_COLORS) == 147
    assert len(SUPPORTED_DISPLAY_COLOR_VALUES) == 147
    assert SUPPORTED_DISPLAY_COLORS[0] == ("AliceBlue", "EFF7FF")
    assert SUPPORTED_DISPLAY_COLORS[-1] == ("YellowGreen", "94CA31")
    assert all(color in SUPPORTED_DISPLAY_COLOR_VALUES for palette in PALETTES for color in palette.colors().values())


def test_supported_colors_are_grouped_by_hue_then_dark_to_light():
    catalog = supported_color_catalog()
    assert len(catalog) == 147
    assert catalog[0]["name"] == "Black"
    assert catalog[0]["sentinel_index"] == 7
    assert [color["index"] for color in catalog] == list(range(147))
    assert [color["family_order"] for color in catalog] == sorted(color["family_order"] for color in catalog)
    for family in {color["family"] for color in catalog}:
        lightness = [color["lightness"] for color in catalog if color["family"] == family]
        assert lightness == sorted(lightness)


def test_generated_display_xml_matches_real_sentinel_export_layout():
    reference = ET.parse(Path(__file__).parents[1] / "docs" / "display.xml").getroot()
    expected = _signature(reference)
    assert expected == SCREEN_SPECS

    for palette in PALETTES:
        generated = ET.fromstring(generate_display_xml(palette))
        assert generated.tag == "UndienScanner"  # Sentinel's exported spelling
        assert generated.attrib == {"Model": "SDS100", "FileType": "DisplayCustomizer"}
        assert _signature(generated) == expected


def test_palette_colors_are_consistent_by_semantic_group_across_screens():
    root = ET.fromstring(generate_display_xml(PALETTES[0]))
    system_colors = {
        item.attrib["Text"]
        for screen in root.findall("Screen")
        for item in screen.findall("Item")
        if item.attrib.get("Name") == "System Name"
    }
    department_colors = {
        item.attrib["Text"]
        for screen in root.findall("Screen")
        for item in screen.findall("Item")
        if item.attrib.get("Name") == "Department Name"
    }
    channel_colors = {
        item.attrib["Text"]
        for screen in root.findall("Screen")
        for item in screen.findall("Item")
        if item.attrib.get("Name") == "Channel Name"
    }
    assert system_colors == {PALETTES[0].system}
    assert department_colors == {PALETTES[0].department}
    assert channel_colors == {PALETTES[0].channel}
    for screen in root.findall("Screen"):
        for item in screen.findall("Item"):
            if item.attrib.get("Name") in ("Sub Info", "Modulation", "Detail Info"):
                assert item.attrib["Text"] == PALETTES[0].channel


def test_custom_item_colors_sync_globally_and_allow_per_view_override():
    config = {
        "name": "Custom",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {"Func": {"text": "EFF7FF", "back": "000000"}},
        "screen_item_colors": {"SimpleTrunk||0": {"text": "F7EBD6"}},
        "global_item_options": {"Option_3": "Time"},
        "screen_item_options": {"SimpleTrunk||3": "GPS"},
    }
    data, _ = generate_custom_display_xml(config)
    root = ET.fromstring(data)
    simple_conventional = root.find("./Screen[@Name='SimpleConventional']/Item[@Name='Func']")
    simple_trunk = root.find("./Screen[@Name='SimpleTrunk']/Item[@Name='Func']")
    detail_trunk = root.find("./Screen[@Name='DetailTrunk']/Item[@Name='Func']")
    simple_conventional_option = root.find("./Screen[@Name='SimpleConventional']/Item[@Name='Option_3']")
    simple_trunk_option = root.find("./Screen[@Name='SimpleTrunk']/Item[@Name='Option_3']")
    detail_trunk_option = root.find("./Screen[@Name='DetailTrunk']/Item[@Name='Option_3']")
    weather_option = root.find("./Screen[@Name='Weather']/Item[@Name='Option_3']")

    assert simple_conventional.attrib["Text"] == "EFF7FF"
    assert detail_trunk.attrib["Text"] == "EFF7FF"
    assert simple_trunk.attrib["Text"] == "F7EBD6"
    assert simple_trunk.attrib["Back"] == "000000"
    assert simple_conventional_option.attrib["Option"] == "Time"
    assert detail_trunk_option.attrib["Option"] == "Time"
    assert simple_trunk_option.attrib["Option"] == "GPS"
    assert weather_option.attrib["Option"] == "Day"


def test_custom_display_rejects_unknown_item_override():
    config = {
        "name": "Invalid",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {"not-an-item": {"text": "FFFFFF"}},
        "screen_item_colors": {},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "unknown item override" in str(exc)
    else:
        raise AssertionError("unknown item override was accepted")


def test_custom_display_rejects_arbitrary_rgb_color():
    config = {
        "name": "Invalid Color",
        "colors": {**PALETTES[0].colors(), "system": "ABCDEF"},
        "global_item_colors": {},
        "screen_item_colors": {},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "not supported by Sentinel" in str(exc)
    else:
        raise AssertionError("arbitrary RGB color was accepted")


def test_custom_display_rejects_non_object_payload():
    try:
        generate_custom_display_xml([])
    except ValueError as exc:
        assert "must be an object" in str(exc)
    else:
        raise AssertionError("non-object custom palette was accepted")


def test_custom_display_rejects_unsupported_option():
    config = {
        "name": "Invalid Option",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
        "global_item_options": {"Option_3": "NotARealOption"},
        "screen_item_options": {},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("unsupported display option was accepted")


def test_custom_display_rejects_option_valid_elsewhere_but_not_for_field():
    config = {
        "name": "Invalid Field Option",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
        "global_item_options": {"Channel option": "WACN"},
        "screen_item_options": {},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("field-incompatible display option was accepted")


def test_weather_and_tone_out_item_options_are_fixed():
    config = {
        "name": "Invalid Weather Option",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
        "global_item_options": {},
        "screen_item_options": {"Weather||3": "Time"},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("Weather item option change was accepted")
