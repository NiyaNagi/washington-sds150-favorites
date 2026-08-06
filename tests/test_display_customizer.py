import xml.etree.ElementTree as ET
from pathlib import Path

from wasds150.display_customizer import (
    PALETTES,
    LAYOUT_TEMPLATES,
    COLOR_GROUPINGS,
    HUGE_OPTION_CHOICES,
    LARGE_OPTION_CHOICES,
    SMALL_OPTION_CHOICES,
    ICON_OPTION_CHOICES,
    SCREEN_SPECS,
    display_layout_catalog,
    generate_custom_display_xml,
    generate_display_xml,
    color_grouping_catalog,
    grouped_category,
    layout_template_catalog,
    option_choices,
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


def test_visual_layouts_cover_every_xml_item_exactly_once():
    layouts = display_layout_catalog()
    assert set(layouts) == set(SCREEN_SPECS)
    for screen_name, items in SCREEN_SPECS.items():
        indices = [index for row in layouts[screen_name] for index in row["indices"]]
        assert sorted(indices) == list(range(len(items)))
        assert len(indices) == len(set(indices))
        assert all(set(row["primary_indices"]).issubset(row["indices"]) for row in layouts[screen_name])


def test_func_uses_standard_text_and_background_mapping_on_every_screen():
    palette = PALETTES[0]
    root = ET.fromstring(generate_display_xml(palette))
    for screen in root.findall("Screen"):
        func = screen.find("./Item[@Name='Func']")
        assert func is not None
        assert func.attrib["Text"] == palette.status
        assert func.attrib["Back"] == palette.background


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
    assert weather_option.attrib["Option"] == "Time"


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


def test_custom_display_rejects_option_from_wrong_sentinel_field_type():
    config = {
        "name": "Invalid Field Option",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
        "global_item_options": {"Channel option": "Battery Current"},
        "screen_item_options": {},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "unsupported" in str(exc)
    else:
        raise AssertionError("field-incompatible display option was accepted")


def test_weather_and_tone_out_blank_slots_accept_their_sentinel_field_type():
    config = {
        "name": "Invalid Weather Option",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
        "global_item_options": {},
        "screen_item_options": {"Weather||8": "P25Status", "Tone out||24": "Frequency"},
    }
    data, _ = generate_custom_display_xml(config)
    root = ET.fromstring(data)
    assert root.find("./Screen[@Name='Weather']/Item[@Name='Option_7']").attrib["Option"] == "P25Status"
    assert root.find("./Screen[@Name='Tone out']/Item[@Name='Option A-1']").attrib["Option"] == "Frequency"


def test_layout_templates_fill_every_editable_slot_with_supported_options():
    assert len(LAYOUT_TEMPLATES) >= 10
    assert len(layout_template_catalog()) == len(LAYOUT_TEMPLATES)
    for template in LAYOUT_TEMPLATES[1:]:
        for screen_name, items in SCREEN_SPECS.items():
            for index, (name, default) in enumerate(items):
                choices = option_choices(name, screen_name, default)
                if not choices:
                    continue
                selected = template.screen_item_options.get(f"{screen_name}||{index}", default)
                assert selected in choices
                assert selected != "Empty"


def test_authoritative_sentinel_option_tables_cover_all_exported_defaults():
    assert len(HUGE_OPTION_CHOICES) == 16
    assert len(LARGE_OPTION_CHOICES) == 33  # Sentinel has 34 rows; Fahrenheit/Celsius share one XML token.
    assert len(SMALL_OPTION_CHOICES) == 20
    assert len(ICON_OPTION_CHOICES) == 13
    for screen_name, items in SCREEN_SPECS.items():
        for name, default in items:
            choices = option_choices(name, screen_name, default)
            if default is not None:
                assert default in choices


def test_layout_templates_are_palette_independent_and_recolor_selected_data_logically():
    config = {
        "name": "Technical",
        "layout_template_id": "technical",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
    }
    dark, _ = generate_custom_display_xml(config)
    config["colors"] = PALETTES[1].colors()
    light, _ = generate_custom_display_xml(config)
    dark_root = ET.fromstring(dark)
    light_root = ET.fromstring(light)
    dark_option_a = dark_root.find("./Screen[@Name='SimpleConventional']/Item[@Name='Option A']")
    dark_option_b = dark_root.find("./Screen[@Name='SimpleConventional']/Item[@Name='Option B']")
    light_option_a = light_root.find("./Screen[@Name='SimpleConventional']/Item[@Name='Option A']")
    assert dark_option_a.attrib["Option"] == light_option_a.attrib["Option"] == "Frequency"
    assert dark_option_a.attrib["Text"] == PALETTES[0].channel
    assert light_option_a.attrib["Text"] == PALETTES[1].channel
    assert dark_option_b.attrib["Option"] == "D_ErrorCount"
    assert dark_option_b.attrib["Text"] == PALETTES[0].metadata


def test_synchronized_and_per_screen_choices_override_template_defaults():
    config = {
        "name": "Technical Customized",
        "layout_template_id": "technical",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
        "global_item_options": {"Option A": "ServiceType"},
        "screen_item_options": {"SimpleTrunk||23": "TGID"},
    }
    data, _ = generate_custom_display_xml(config)
    root = ET.fromstring(data)
    assert root.find("./Screen[@Name='SimpleConventional']/Item[@Name='Option A']").attrib["Option"] == "ServiceType"
    assert root.find("./Screen[@Name='SimpleTrunk']/Item[@Name='Option A']").attrib["Option"] == "TGID"


def test_custom_display_rejects_unknown_layout_template():
    config = {
        "name": "Unknown Layout",
        "layout_template_id": "not-a-layout",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "unknown display layout template" in str(exc)
    else:
        raise AssertionError("unknown layout template was accepted")


def test_color_groupings_offer_basic_colorful_rows_scenarios_and_accessibility():
    assert len(COLOR_GROUPINGS) >= 10
    assert len(color_grouping_catalog()) == len(COLOR_GROUPINGS)
    assert {grouping.style for grouping in COLOR_GROUPINGS} >= {
        "Basic", "Colorful", "Rows", "Scenario", "Accessibility",
    }
    full = next(grouping for grouping in COLOR_GROUPINGS if grouping.id == "full-spectrum")
    for screen_name, items in SCREEN_SPECS.items():
        for index, (name, option) in enumerate(items):
            if name in ("SP0", "SP1", "SP2") or option == "Empty":
                continue
            category = grouped_category(full, screen_name, index, name, option)
            assert category in {"system", "department", "channel", "metadata", "alert", "accent"}


def test_color_grouping_changes_colors_without_changing_layout_or_theme_values():
    config = {
        "name": "Grouped",
        "layout_template_id": "technical",
        "color_grouping_id": "row-bands",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
    }
    grouped, _ = generate_custom_display_xml(config)
    config["color_grouping_id"] = "balanced"
    balanced, _ = generate_custom_display_xml(config)
    grouped_root = ET.fromstring(grouped)
    balanced_root = ET.fromstring(balanced)
    grouped_items = grouped_root.findall("./Screen[@Name='SimpleConventional']/Item")
    balanced_items = balanced_root.findall("./Screen[@Name='SimpleConventional']/Item")
    assert [(item.attrib["Name"], item.attrib.get("Option")) for item in grouped_items] == [
        (item.attrib["Name"], item.attrib.get("Option")) for item in balanced_items
    ]
    assert grouped_items[0].attrib["Text"] == PALETTES[0].accent
    assert grouped_items[-1].attrib["Text"] == PALETTES[0].alert
    assert grouped_items[0].attrib["Text"] != balanced_items[0].attrib["Text"]


def test_every_grouping_generates_valid_xml_with_every_palette():
    for grouping in COLOR_GROUPINGS:
        for palette in PALETTES:
            assert validate_display_xml(generate_display_xml(palette, color_grouping_id=grouping.id)) == []


def test_custom_display_rejects_unknown_color_grouping():
    config = {
        "name": "Unknown Grouping",
        "color_grouping_id": "not-a-grouping",
        "colors": PALETTES[0].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
    }
    try:
        generate_custom_display_xml(config)
    except ValueError as exc:
        assert "unknown display color grouping" in str(exc)
    else:
        raise AssertionError("unknown color grouping was accepted")
