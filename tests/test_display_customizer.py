import xml.etree.ElementTree as ET
from pathlib import Path

from wasds150.display_customizer import (
    PALETTES,
    SCREEN_SPECS,
    generate_custom_display_xml,
    generate_display_xml,
    palette_summary,
    validate_display_xml,
    validate_palette,
)


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
        "global_item_colors": {"Func||": {"text": "ABCDEF", "back": "101010"}},
        "screen_item_colors": {"SimpleTrunk||0": {"text": "FEDCBA"}},
    }
    data, _ = generate_custom_display_xml(config)
    root = ET.fromstring(data)
    simple_conventional = root.find("./Screen[@Name='SimpleConventional']/Item[@Name='Func']")
    simple_trunk = root.find("./Screen[@Name='SimpleTrunk']/Item[@Name='Func']")
    detail_trunk = root.find("./Screen[@Name='DetailTrunk']/Item[@Name='Func']")

    assert simple_conventional.attrib["Text"] == "ABCDEF"
    assert detail_trunk.attrib["Text"] == "ABCDEF"
    assert simple_trunk.attrib["Text"] == "FEDCBA"
    assert simple_trunk.attrib["Back"] == "101010"


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


def test_custom_display_rejects_non_object_payload():
    try:
        generate_custom_display_xml([])
    except ValueError as exc:
        assert "must be an object" in str(exc)
    else:
        raise AssertionError("non-object custom palette was accepted")
