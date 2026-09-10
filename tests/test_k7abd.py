"""K7ABD Config Builder parsing, the seattledmr source, and the DMR network lists."""
from __future__ import annotations

from wasds150.catalog.atd890_dmr import REPEATERS, TALKGROUPS, favorites
from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.recipes.dmr_networks import build_network_favorites, coordinate_lookup_from_catalog
from wasds150.sources.base import RawDoc
from wasds150.sources.k7abd import (
    SeattleDmrSource,
    facts_from_k7abd,
    parse_analog,
    parse_digital_repeaters,
    parse_talkgroups,
    site_tokens,
    talkgroup_short_name,
)

REPEATERS_CSV = (
    "Zone Name,Comment,Power,RX Freq,TX Freq,Color Code,Washington 1,Washington 2,TAC 310-2,I-5 1\n"
    "Bellevu/Cougar;BVV,,High,147.02,147.62,1,1,2,2,1\n"
    "Pullman/Pullman;PUW,,High,440.7,445.7,1,1,2,-,-\n"
    "MM/Demi 2Slot;MMD,,High,430.4375,439.4375,1,1,2,2,-\n"
    "N Bend/Vly Camp,,High,440.725,445.725,1,1,2,-,1\n"
)
TALKGROUPS_CSV = "Washington 1,3153\nWashington 2,103153\nTAC 310-2,310\nI-5 1,3168\nSimplex 99, 99\n"
ANALOG_CSV = (
    "Zone,Channel Name,Bandwidth,Power,RX Freq,TX Freq,CTCSS Decode,CTCSS Encode,TX Prohibit\n"
    "ACS VHF,V01 PSRG,25K,High,146.96,146.36,Off,103.5,Off\n"
    "ACS VHF,V71 Lynwood,25K,High,146.78,146.18,Off,D172N,Off\n"
    "FRS,FRS 1,12.5K,Low,462.5625,462.5625,Off,Off,On\n"
)


class TestParsing:
    def test_repeaters(self):
        rows = parse_digital_repeaters(REPEATERS_CSV)
        assert [r.code for r in rows] == ["BVV", "PUW", "MMD", "NBV"]
        cougar = rows[0]
        assert (cougar.rx_mhz, cougar.tx_mhz, cougar.color_code) == (147.02, 147.62, 1)
        assert cougar.slots == {"Washington 1": 1, "Washington 2": 2, "TAC 310-2": 2, "I-5 1": 1}
        assert cougar.region == "Puget Sound" and cougar.network == "PNWDigital"
        assert rows[1].region == "Eastern Washington"
        assert rows[2].is_hotspot and not cougar.is_hotspot
        assert rows[3].region == "Puget Sound"

    def test_talkgroups_and_names(self):
        tgs = {t.name: t.tg_id for t in parse_talkgroups(TALKGROUPS_CSV)}
        assert tgs == {"Washington 1": 3153, "Washington 2": 103153, "TAC 310-2": 310, "I-5 1": 3168, "Simplex 99": 99}
        assert talkgroup_short_name("TAC 310-2") == "TAC 310"
        assert talkgroup_short_name("I-5 1") == "I-5 1"
        assert talkgroup_short_name("Local 2") == "Local 2"
        assert talkgroup_short_name("Hawaii 1-2") == "Hawaii 1"

    def test_analog(self):
        rows = parse_analog(ANALOG_CSV)
        assert rows[0].tx_tone == "TONE=C103.5" and rows[0].rx_tone == ""
        assert rows[1].tx_tone == "D172"
        assert rows[2].tx_prohibit and rows[2].bandwidth == "12.5K"

    def test_site_tokens(self):
        rows = {r.code: r for r in parse_digital_repeaters(REPEATERS_CSV)}
        assert "cougar" in site_tokens(rows["BVV"])
        assert {"north", "bend", "camp"} <= site_tokens(rows["NBV"])


class TestFactsAndLists:
    def _facts(self):
        tgs = {t.name: t for t in parse_talkgroups(TALKGROUPS_CSV)}
        return list(facts_from_k7abd(parse_digital_repeaters(REPEATERS_CSV), tgs, parse_analog(ANALOG_CSV)))

    def test_facts(self):
        facts = self._facts()
        digital = [f for f in facts if f.raw["kind"] == "digital"]
        # 4 + 2 + 3 talkgroups; the hotspot is skipped.
        assert len(digital) == 9
        first = digital[0]
        assert first.name == "I-5 1 BVV" and first.mode == "DMR" and first.tone == "ColorCode=1"
        assert (first.dmr_talkgroup, first.dmr_timeslot, first.tx_freq_mhz) == (3168, 1, 147.62)
        analog = [f for f in facts if f.raw["kind"] == "analog"]
        assert analog[0].raw["tx_tone"] == "TONE=C103.5" and analog[0].mode == "FM"

    def test_coordinates_join_by_site_word(self):
        wwara = Department(id="w", label="DMR", channels=[
            Channel(id="c1", label="WA7DMR - Cougar Mtn", freq_mhz=147.02, mode="DMR", tone="ColorCode=1", lat=47.542, lon=-122.109),
            Channel(id="c2", label="N7ER - Clinton", freq_mhz=440.7, mode="DMR", tone="ColorCode=1", lat=47.9565, lon=-122.3732),
        ])
        catalog = Catalog(favorites=[FavoritesList(
            id="f", slug="psham01", favorite_key="PSHAM01", favorite_name="", region="", counties="", scenario="",
            source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
            monitorability="", upgrade_required="", source_url="", notes="",
            systems=[System(id="s", label="s", departments=[wwara])])])
        lists = build_network_favorites(self._facts(), coords=coordinate_lookup_from_catalog(catalog))
        dmrnet = next(fl for fl in lists if fl.favorite_key == "DMRNET")
        channels = {c.label: c for d in dmrnet.systems[0].departments for c in d.channels}
        assert channels["Washington 1 BVV"].lat == 47.542
        # Pullman shares Clinton's pair and colour code but not its site: no position.
        assert channels["Washington 1 PUW"].lat is None
        assert [d.label for d in dmrnet.systems[0].departments] == ["Puget Sound", "Eastern Washington"]
        seaacs = next(fl for fl in lists if fl.favorite_key == "SEAACS")
        acs = {c.label: c for d in seaacs.systems[0].departments for c in d.channels}
        assert acs["V01 PSRG"].tx_tone == "TONE=C103.5" and acs["V01 PSRG"].tx_freq_mhz == 146.36

    def test_source_normalize(self):
        source = SeattleDmrSource()
        raw = RawDoc(source_adapter="seattledmr", payload={
            "digital_repeaters": REPEATERS_CSV, "talkgroups": TALKGROUPS_CSV, "analog": ANALOG_CSV,
        }, fetched_at="2026-09-10T00:00:00+00:00")
        result = source.normalize(raw)
        assert len(result.facts) == 12 and result.facts[0].source_id == "seattledmr"


class TestSnapshot:
    def test_snapshot_is_in_scope_and_positioned(self):
        codes = {r[1] for r in REPEATERS}
        assert {"BVV", "BVC", "SCE", "LFP", "SWE", "KNW", "TBU", "SUL", "NBV"} <= codes
        assert "MMD" not in codes and "HOT" not in codes and "POM" not in codes
        assert TALKGROUPS["Washington 1"] == 3153 and TALKGROUPS["King County"] == 333153
        positioned = [r for r in REPEATERS if r[5] is not None]
        assert len(positioned) >= 15
        lists = favorites()
        assert [fl.favorite_key for fl in lists] == ["DMRNET", "SEAACS"]
        puget = next(d for d in lists[0].systems[0].departments if d.label == "Puget Sound")
        assert len(puget.channels) > 300
        for channel in puget.channels:
            assert channel.dmr_talkgroup and channel.dmr_timeslot in (1, 2) and channel.tx_freq_mhz
            assert "seattledmr.com" in channel.notes
