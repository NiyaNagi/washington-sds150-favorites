import base64
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from wasds150.display_customizer import (
    PALETTES,
    display_item_catalog,
    generate_custom_display_xml,
)


SENTINEL_EXE = Path(r"C:\Program Files (x86)\Uniden\BCDx36HP Sentinel\BCDx36HP_Sentinel.exe")
POWERSHELL_X86 = Path(os.environ.get("WINDIR", r"C:\Windows")) / "SysWOW64" / "WindowsPowerShell" / "v1.0" / "powershell.exe"


@pytest.mark.skipif(
    os.name != "nt" or not SENTINEL_EXE.is_file() or not POWERSHELL_X86.is_file(),
    reason="installed x86 BCDx36HP Sentinel is required",
)
def test_generated_xml_roundtrips_through_sentinel_parser(tmp_path):
    source = tmp_path / "generated-display.xml"
    exported = tmp_path / "sentinel-exported-display.xml"
    config = {
        "name": "Sentinel Roundtrip",
        "layout_template_id": "technical",
        "color_grouping_id": "stable-item-rainbow",
        "colors": PALETTES[6].colors(),
        "global_item_colors": {},
        "screen_item_colors": {},
    }
    source.write_bytes(generate_custom_display_xml(config)[0])

    script = f'''
$a=[Reflection.Assembly]::LoadFrom("{SENTINEL_EXE}")
$t=$a.GetType("HomePatrol_Sentinel.XmlDipalpyCustomizer")
$x=[Activator]::CreateInstance($t)
$t.GetMethod("Import").Invoke($x,@("{source}"))
$t.GetMethod("Export").Invoke($x,@("{exported}"))
'''
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        [str(POWERSHELL_X86), "-NoProfile", "-STA", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert exported.is_file()

    source_root = ET.parse(source).getroot()
    exported_root = ET.parse(exported).getroot()
    catalog = display_item_catalog()
    assert [screen.attrib["Name"] for screen in source_root] == [screen.attrib["Name"] for screen in exported_root]

    for source_screen, exported_screen in zip(source_root, exported_root):
        screen_name = source_screen.attrib["Name"]
        assert len(source_screen) == len(exported_screen) == len(catalog[screen_name])
        for item_meta, source_item, exported_item in zip(catalog[screen_name], source_screen, exported_screen):
            assert source_item.attrib["Name"] == exported_item.attrib["Name"]
            assert source_item.attrib.get("Option") == exported_item.attrib.get("Option")
            if item_meta["xml_import_color_supported"]:
                assert source_item.attrib["Text"] == exported_item.attrib["Text"]
                assert source_item.attrib["Back"] == exported_item.attrib["Back"]
