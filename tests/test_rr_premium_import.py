"""RadioReference Premium export import and the per-county lists built from it.

Fixtures here mirror the *layout* of a real RadioReference CSV export (header
names, tone spellings, mode labels) with made-up rows, so no licensed data is
committed.
"""
from __future__ import annotations

import pytest

from wasds150.recipes.engine import enrich_catalog
from wasds150.recipes.rr_county import build_rr_favorites, county_key
from wasds150.sources.radioreference_premium import (
    RadioReferencePremiumSource,
    county_from_filename,
    normalize_mode,
    parse_rr_tone,
)

COUNTY_HEADER = (
    '"Frequency Output","Frequency Input","FCC Callsign",Agency/Category,Description,'
    '"Alpha Tag","PL Output Tone","PL Input Tone",Mode,"Class Station Code",Tag\n'
)
STATE_HEADER = (
    '"Frequency Output","Frequency Input","FCC Callsign",Agency/Category,County,Description,'
    '"Alpha Tag","PL Output Tone","PL Input Tone",Mode,"Class Station Code",Tag\n'
)

COUNTY_ROWS = (
    '146.520000,0.00000,,"2 Meters","Simplex calling","2m Call",CSQ,,FM,BM,Ham\n'
    '147.020000,147.62000,WA7DMR,"2 Meters","Cougar Mtn DMR","Cougar DMR","CC 1|TG 3153|SL 1","CC 1|TG 3153|SL 1",DMR,RM,Ham\n'
    '152.337500,157.59750,KAB123,"Seattle EMS","AMR Ambulance Ch 1","AMR Ch 1","37 RAN",,NXDN48,BM,EMS Dispatch\n'
    '118.300000,0.00000,,"Airports Air Traffic Control","Tower","Twr",CSQ,,AM,BM,Aircraft\n'
    '154.905000,155.37000,KOE666,"Example Sheriff","Dispatch","Disp","103.5 PL","023 DPL",FMN,RM,Law Dispatch\n'
    '146.475000,147.47500,,"2 Meters","Cougar P25","Cougar P25","293 NAC","293 NAC",P25,RM,Ham\n'
    '167.000000,0.00000,,"Justice Integrated Wireless Network","Site 018 Cougar Mtn, WA",,n/a,n/a,"Project 25",,TRS\n'
    '0.000000,0.00000,,"Broken","No frequency",,,,FM,,Other\n'
)
STATE_ROWS = (
    '31.100000,0.00000,,"Airports Paine Field",Statewide,"Washington Air National Guard","W Nat Gd",,,FM,BM,Aircraft\n'
    '146.520000,0.00000,,"2 Meters",King,"Simplex calling","2m Call",CSQ,,FM,BM,Ham\n'
    '453.100000,458.10000,WNAB999,"Asotin County Sheriff",Asotin,"Dispatch","ASO Disp","D4B NAC",,P25,RM,Law Dispatch\n'
    '145.130000,144.53000,K7LWH,"2 Meters",King,"Lake Washington Ham Club","K7LWH DSTAR",,,D-STAR,RM,Ham\n'
)


@pytest.fixture()
def export_dir(tmp_path):
    (tmp_path / "ctid_2974_1789071476.csv").write_text(COUNTY_HEADER + COUNTY_ROWS, encoding="utf-8")
    (tmp_path / "stid_531789071493.csv").write_text(STATE_HEADER + STATE_ROWS, encoding="utf-8")
    return tmp_path


class TestToneParsing:
    @pytest.mark.parametrize(
        "text,tone,cc,tg,slot,ran",
        [
            ("103.5 PL", "TONE=C103.5", None, None, None, None),
            ("100.0 PL", "TONE=C100", None, None, None, None),
            ("023 DPL", "D023", None, None, None, None),
            ("293 NAC", "NAC=293", None, None, None, None),
            ("D4B NAC", "NAC=D4B", None, None, None, None),
            ("37 RAN", "", None, None, None, 37),
            ("CC 1|TG 9|SL 2", "ColorCode=1", 1, 9, 2, None),
            ("CC 2|TG *|SL *", "ColorCode=2", 2, None, None, None),
            ("CSQ", "", None, None, None, None),
            ("n/a", "", None, None, None, None),
            ("", "", None, None, None, None),
        ],
    )
    def test_radioreference_tone_spellings(self, text, tone, cc, tg, slot, ran):
        parsed = parse_rr_tone(text)
        assert parsed.tone == tone
        assert parsed.color_code == cc
        assert parsed.talkgroup == tg
        assert parsed.slot == slot
        assert parsed.ran == ran


class TestModeAndCounty:
    @pytest.mark.parametrize(
        "text,mode",
        [
            ("FM", "FM"), ("FMN", "NFM"), ("AM", "AM"), ("DMR", "DMR"), ("NXDN48", "NXDN"),
            ("NXDN", "NXDN"), ("P25", "P25"), ("Project 25", "P25"), ("P25E", "P25"),
            ("D-STAR", "AUTO"), ("MPT-1327", "AUTO"), ("", "AUTO"),
        ],
    )
    def test_modes_map_to_catalog_vocabulary(self, text, mode):
        assert normalize_mode(text) == mode

    def test_county_from_filename(self):
        assert county_from_filename("ctid_2974_1789071476.csv") == "King"
        assert county_from_filename("rr-snohomish-county-20260910.csv") == "Snohomish"
        assert county_from_filename("stid_531789071493.csv") == "Statewide"
        assert county_from_filename("ctid_1_x.csv") is None


class TestImport:
    def test_reads_every_export_in_a_directory(self, export_dir):
        source = RadioReferencePremiumSource(export_path=export_dir)
        result = source.normalize(source.fetch())
        freqs = [f for f in result.facts if f.fact_type == "frequency"]
        sites = [f for f in result.facts if f.fact_type == "site"]
        # 7 county rows with a frequency (one is the trunked site) + 4 state
        # rows, minus the state row that duplicates the county simplex entry.
        assert len(freqs) == 9
        assert len(sites) == 1
        assert any("verified RadioReference export layout" in w for w in result.warnings)

    def test_county_export_takes_county_from_filename(self, export_dir):
        source = RadioReferencePremiumSource(export_path=export_dir / "ctid_2974_1789071476.csv")
        result = source.normalize(source.fetch())
        assert {f.county for f in result.facts} == {"King"}

    def test_digital_identity_survives(self, export_dir):
        source = RadioReferencePremiumSource(export_path=export_dir / "ctid_2974_1789071476.csv")
        facts = {f.name: f for f in source.normalize(source.fetch()).facts}
        dmr = facts["Cougar Mtn DMR"]
        assert dmr.mode == "DMR"
        assert dmr.tone == "ColorCode=1"
        assert (dmr.dmr_color_code, dmr.dmr_talkgroup, dmr.dmr_timeslot) == (1, 3153, 1)
        assert dmr.tx_freq_mhz == pytest.approx(147.62)
        nxdn = facts["AMR Ambulance Ch 1"]
        assert nxdn.mode == "NXDN"
        assert nxdn.nxdn_ran == 37
        assert nxdn.tone is None
        analog = facts["Dispatch"]
        assert analog.tone == "TONE=C103.5"
        assert analog.raw["tx_tone"] == "D023"
        assert analog.mode == "NFM"

    def test_rows_without_a_frequency_are_skipped(self, export_dir):
        source = RadioReferencePremiumSource(export_path=export_dir / "ctid_2974_1789071476.csv")
        result = source.normalize(source.fetch())
        assert all(f.freq_mhz for f in result.facts)
        assert any("1 rows without a frequency skipped" in w for w in result.warnings)


class TestCountyLists:
    def _facts(self, export_dir):
        source = RadioReferencePremiumSource(export_path=export_dir)
        return source.normalize(source.fetch()).facts

    def test_one_list_per_county_plus_statewide(self, export_dir):
        lists = build_rr_favorites(self._facts(export_dir))
        keys = sorted(fl.favorite_key for fl in lists)
        assert keys == ["RRC-ASOTIN", "RRC-KING", "RRWA"]
        assert county_key("Grays Harbor") == "RRC-GRAYSHARBOR"
        for fl in lists:
            assert fl.licensed
            assert fl.origin == "local"
            assert fl.systems and fl.systems[0].departments

    def test_channels_keep_digital_fields_and_geo_fence(self, export_dir):
        lists = {fl.favorite_key: fl for fl in build_rr_favorites(self._facts(export_dir))}
        king = lists["RRC-KING"]
        channels = {c.label: c for d in king.systems[0].departments for c in d.channels}
        assert channels["Cougar Mtn DMR"].dmr_talkgroup == 3153
        assert channels["Cougar Mtn DMR"].tx_freq_mhz == pytest.approx(147.62)
        assert channels["AMR Ambulance Ch 1"].nxdn_ran == 37
        assert channels["Dispatch"].tx_tone == "D023"
        assert channels["Lake Washington Ham Club"].mode == "AUTO"
        # Trunked site rows never become channels.
        assert "Site 018 Cougar Mtn, WA" not in channels
        dept = king.systems[0].departments[0]
        assert dept.lat == pytest.approx(47.490552) and dept.range_miles == pytest.approx(26.0)

    def test_far_counties_start_disabled_near_home(self, export_dir):
        lists = {fl.favorite_key: fl for fl in build_rr_favorites(
            self._facts(export_dir), home=(47.6351, -121.9954), enable_within_miles=60.0
        )}
        assert lists["RRC-KING"].enabled
        assert lists["RRWA"].enabled
        assert not lists["RRC-ASOTIN"].enabled

    def test_enrich_catalog_appends_and_replaces_rr_lists(self, export_dir):
        from wasds150.models.catalog import Catalog

        facts = self._facts(export_dir)
        first = enrich_catalog(Catalog(favorites=[]), facts, recipes=[]).catalog
        assert {fl.favorite_key for fl in first.favorites} == {"RRC-ASOTIN", "RRC-KING", "RRWA"}
        # A user who enabled a far county keeps that choice across a refresh.
        for fl in first.favorites:
            if fl.favorite_key == "RRC-ASOTIN":
                fl.enabled = True
        second = enrich_catalog(first, facts, recipes=[]).catalog
        assert len(second.favorites) == 3
        assert next(fl for fl in second.favorites if fl.favorite_key == "RRC-ASOTIN").enabled
        # Without RadioReference facts the previous lists survive untouched.
        third = enrich_catalog(second, [], recipes=[]).catalog
        assert len(third.favorites) == 3

    def test_rr_lists_validate_for_the_scanner(self, export_dir):
        from wasds150.hpe.validation import validate_favorites_list

        for fl in build_rr_favorites(self._facts(export_dir)):
            assert validate_favorites_list(fl) == []
