"""Where a fleet export lands besides the output folder."""
from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.contacts.model import ContactStore
from wasds150.contacts.radioid import parse_contacts
from wasds150.fleet.registry import FLEET
from wasds150.fleet.service import export_radio
from wasds150.fleet.settings import FleetSettings


def test_every_memory_radio_can_copy_its_file_to_the_programming_folder():
    for radio_id in ("td-h9", "th-d75", "ftx1", "at-d890uv"):
        assert FLEET[radio_id].input("copy_to") is not None, radio_id


def test_anytone_export_keeps_a_standing_copy_of_the_contact_lists(tmp_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    ctx = build_context(config)
    store = ContactStore(config.contacts_dir)
    store.save(parse_contacts("RADIO_ID,CALLSIGN\n3227807,WA7DAM\n", "DMR"))
    store.save(parse_contacts("RADIO_ID,CALLSIGN\n16240,WA7DAM\n", "NXDN"))
    settings = FleetSettings()
    settings.set("at-d890uv", "contacts_to", str(tmp_path / "kept"))
    settings.save(config.fleet_settings_path)

    export = export_radio(ctx, "at-d890uv", out_dir=tmp_path / "out")

    kept = sorted(p.name for p in (tmp_path / "kept").iterdir())
    assert kept == ["DigitalContactList.CSV", "NXDNContactList.CSV"]
    assert all(tmp_path / "kept" / name in export.copies for name in kept)
    assert "3227807" in (tmp_path / "kept" / "DigitalContactList.CSV").read_text(encoding="ascii")
