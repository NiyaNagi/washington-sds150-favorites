import xml.etree.ElementTree as ET
from pathlib import Path

from wasds150.display_customizer import (
    PALETTES,
    SCREEN_SPECS,
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
    assert len(PALETTES) >= 4
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
