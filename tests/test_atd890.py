"""Anytone AT-D890UV: profile, digital identity, bundle derivation and CPS CSV."""
from __future__ import annotations

import csv
import io

import pytest

from wasds150.export.atd890_bundle import (
    AM_ZONE_MEMBER_MAX,
    Atd890ExportError,
    build_bundle,
    route,
)
from wasds150.export.atd890_cps import (
    CHANNEL_DEFAULTS,
    CHANNEL_HEADER,
    ZONE_HEADER,
    AMZONE_HEADER,
    render_files,
    write_atd890,
)
from wasds150.export.registry import get_target
from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import (
    SORT_FREQ,
    TX_NONE,
    TX_REPEATER,
    TX_SIMPLEX,
    ChannelPlan,
    ChannelSelector,
    PlanBlock,
    ScanGroup,
)
from wasds150.plan.naming import shorten_name
from wasds150.plan.resolve import resolve_plan
from wasds150.radios.digital import describe, digital_identity, digital_spec, ran_from_text
from wasds150.radios.registry import AT_D890UV, TD_H9, get_profile


def make_channel(label, freq, **kwargs):
    return Channel(id=kwargs.pop("id", label.lower().replace(" ", "-")), label=label, freq_mhz=freq, **kwargs)


def make_catalog(*channels, favorite_key="FLXX", department="Test Dept"):
    dept = Department(id="d1", label=department, channels=list(channels))
    system = System(id="s1", label="Test System", departments=[dept])
    favorite = FavoritesList(
        id="f1", slug=favorite_key.lower(), favorite_key=favorite_key,
        favorite_name="Test", region="", counties="", scenario="", source_type="",
        system_or_category="", sites_or_coverage="", departments_or_channels="",
        mode="", monitorability="", upgrade_required="", source_url="", notes="",
        systems=[system],
    )
    return Catalog(favorites=[favorite])


ALL = ChannelSelector(favorite_keys=("FLXX",))


def plan(*blocks, scan_groups=()):
    return ChannelPlan(id="atd890-test", radio_id="at-d890uv", label="Test", blocks=tuple(blocks), scan_groups=tuple(scan_groups))


def dmr(label, freq, tx, tg, ts, cc=1, name="", network="PNWDigital", **kw):
    return make_channel(
        label, freq, tx_freq_mhz=tx, mode="DMR", tone=f"ColorCode={cc}",
        dmr_color_code=cc, dmr_timeslot=ts, dmr_talkgroup=tg, dmr_talkgroup_name=name or f"TG {tg}",
        network=network, **kw,
    )


class TestProfile:
    def test_registered(self):
        assert get_profile("at-d890uv") is AT_D890UV

    @pytest.mark.parametrize("freq", [121.5, 146.52, 162.55, 462.5625, 97.3, 108.0])
    def test_receives(self, freq):
        assert AT_D890UV.can_receive(freq)

    @pytest.mark.parametrize("freq", [27.185, 45.2, 223.5, 773.10625, 851.0125])
    def test_does_not_receive(self, freq):
        assert not AT_D890UV.can_receive(freq)

    def test_no_p25(self):
        assert not AT_D890UV.supports_mode("P25")
        assert AT_D890UV.supports_mode("DMR") and AT_D890UV.supports_mode("NXDN")

    def test_transmit_is_amateur_only(self):
        assert AT_D890UV.can_transmit(146.52) and AT_D890UV.can_transmit(446.0)
        assert not AT_D890UV.can_transmit(462.5625)
        assert not AT_D890UV.can_transmit(223.5)

    def test_structure_limits(self):
        assert (AT_D890UV.max_channels, AT_D890UV.name_max_len) == (4000, 16)
        assert (AT_D890UV.zone_max, AT_D890UV.zone_member_max, AT_D890UV.scan_list_member_max) == (250, 160, 100)
        assert AT_D890UV.name_style == "readable"
        assert TD_H9.zone_max is None and TD_H9.name_style == "compact"
        assert not AT_D890UV.verified


class TestDigitalSpec:
    def test_explicit_fields_win(self):
        channel = dmr("Cougar WA1", 147.02, 147.62, 3153, 1, name="Washington 1")
        spec = digital_spec(channel, "DMR")
        assert (spec.color_code, spec.timeslot, spec.talkgroup, spec.talkgroup_name) == (1, 1, 3153, "Washington 1")
        assert spec.has_contact
        assert describe(spec) == "CC1 TS1 TG3153 Washington 1"

    def test_color_code_falls_back_to_tone(self):
        channel = make_channel("Bare", 441.35, mode="DMR", tone="ColorCode=7")
        spec = digital_spec(channel, "DMR")
        assert spec.color_code == 7 and not spec.has_contact

    def test_nxdn_ran_from_text_and_field(self):
        assert ran_from_text("AMR NXDN RAN14") == 14
        assert ran_from_text("Ch1 dispatch,NXDN48") is None
        channel = make_channel("AMR", 152.3375, mode="NXDN", nxdn_ran=37)
        assert digital_spec(channel, "NXDN").ran == 37
        assert describe(digital_spec(channel, "NXDN")) == "RAN37"

    def test_analog_has_no_spec(self):
        assert digital_spec(make_channel("FM", 146.52, mode="FM"), "FM") is None
        assert digital_identity(None) == ()

    def test_identity_includes_colour_code(self):
        a = digital_spec(dmr("A", 147.02, 147.62, 3153, 1, cc=1), "DMR")
        b = digital_spec(dmr("B", 147.02, 147.62, 3153, 1, cc=2), "DMR")
        assert digital_identity(a) != digital_identity(b)


class TestResolver:
    def test_two_talkgroups_on_one_repeater_coexist(self):
        catalog = make_catalog(
            dmr("Cougar WA1", 147.02, 147.62, 3153, 1, name="Washington 1"),
            dmr("Cougar WA2", 147.02, 147.62, 103153, 2, name="Washington 2", id="c2"),
        )
        resolved = resolve_plan(plan(PlanBlock("DMR", (ALL,), tx_policy=TX_REPEATER)), catalog)
        assert resolved.slots_used == 2
        assert all(c.transmit for c in resolved.channels)
        assert resolved.channels[0].digital.talkgroup == 3153
        assert resolved.channels[1].input_freq_mhz == pytest.approx(147.62)
        assert not [w for w in resolved.warnings if "not analog squelch" in w]

    def test_bare_row_is_covered_by_talkgroup_channel(self):
        catalog = make_catalog(
            dmr("Cougar WA1", 147.02, 147.62, 3153, 1),
            make_channel("WA7DMR Cougar", 147.02, tx_freq_mhz=147.62, mode="DMR", tone="ColorCode=1"),
        )
        resolved = resolve_plan(plan(PlanBlock("DMR", (ALL,), tx_policy=TX_REPEATER)), catalog)
        assert resolved.slots_used == 1
        assert resolved.dropped[0].reason == "duplicate"
        assert "covered by talkgroup" in resolved.dropped[0].detail

    def test_dmr_without_talkgroup_is_receive_only(self):
        catalog = make_catalog(make_channel("Bare", 441.35, tx_freq_mhz=446.35, mode="DMR", tone="ColorCode=1"))
        resolved = resolve_plan(plan(PlanBlock("DMR", (ALL,), tx_policy=TX_REPEATER)), catalog)
        assert not resolved.channels[0].transmit
        assert resolved.channels[0].input_freq_mhz == pytest.approx(446.35)
        assert any("no talkgroup" in w for w in resolved.warnings)

    def test_nxdn_never_transmits_and_p25_is_dropped(self):
        catalog = make_catalog(
            make_channel("AMR", 152.3375, tx_freq_mhz=157.5975, mode="NXDN", nxdn_ran=37),
            make_channel("Cougar P25", 146.475, mode="P25", tone="NAC=293"),
        )
        resolved = resolve_plan(plan(PlanBlock("X", (ALL,), tx_policy=TX_REPEATER)), catalog)
        assert resolved.slots_used == 1
        assert not resolved.channels[0].transmit
        assert resolved.dropped[0].reason == "unsupported-mode"

    def test_td_h9_still_drops_dmr(self):
        catalog = make_catalog(dmr("Cougar WA1", 147.02, 147.62, 3153, 1))
        h9 = ChannelPlan(id="h9", radio_id="td-h9", label="t", blocks=(PlanBlock("X", (ALL,)),))
        resolved = resolve_plan(h9, catalog)
        assert resolved.slots_used == 0 and resolved.dropped[0].reason == "unsupported-mode"

    def test_readable_names(self):
        assert shorten_name("Audio Test 2 TBV", 16, readable=True) == "Audio Test 2 TBV"
        assert shorten_name("I-5 1 TBV", 16, readable=True) == "I-5 1 TBV"
        assert shorten_name("W7JCR - Port Townsend", 16, readable=True) == "W7JCR Prt Twnsnd"
        assert shorten_name("Olympic National Park Dispatch", 16, readable=True) == "OLY PK DISP"
        # Compact style is unchanged for the small displays.
        assert shorten_name("SAR 1", 8) == "SAR1"


def _scanner_plan():
    return plan(
        PlanBlock("Ham", (ChannelSelector(favorite_keys=("FLXX",), department_pattern="Ham"),),
                  tx_policy=TX_REPEATER, power="High", bank="Ham 2m", sort=SORT_FREQ),
        PlanBlock("Air", (ChannelSelector(favorite_keys=("FLXX",), department_pattern="Air"),),
                  tx_policy=TX_NONE, bank="Air Civil"),
        PlanBlock("Broadcast", (ChannelSelector(favorite_keys=("FLXX",), department_pattern="Broadcast"),),
                  tx_policy=TX_NONE, bank="FM Bcast", skip_scan=True),
        PlanBlock("NOAA", (ChannelSelector(favorite_keys=("FLXX",), department_pattern="NOAA"),),
                  tx_policy=TX_NONE, bank="NOAA WX", skip_scan=True),
        scan_groups=(ScanGroup("Ham All", ("Ham",)), ScanGroup("Everything", ("Ham", "Air", "NOAA"))),
    )


def _scanner_catalog(n_ham=3):
    ham = Department(id="ham", label="Ham", channels=[
        dmr("Cougar WA1", 147.02, 147.62, 3153, 1, name="Washington 1", id="d1"),
        dmr("Central KC", 440.775, 445.775, 333153, 2, cc=2, name="King County", network="SeattleDMR", id="d2"),
        make_channel("WW7PSR Seattle", 146.96, tx_freq_mhz=146.36, mode="FM", tone="TONE=C103.5", id="a1"),
        make_channel("Bare DMR", 441.35, tx_freq_mhz=446.35, mode="DMR", tone="ColorCode=1", id="a2"),
    ] + [make_channel(f"Rptr {i}", 442.0 + i * 0.025, tx_freq_mhz=447.0 + i * 0.025, mode="NFM", id=f"r{i}") for i in range(n_ham)])
    air = Department(id="air", label="Air", channels=[
        make_channel(f"Tower {i}", 118.3 + i * 0.1, mode="AM", id=f"t{i}") for i in range(40)
    ])
    bc = Department(id="bc", label="Broadcast", channels=[make_channel("KNKX", 88.5, mode="WFM", id="b1")])
    wx = Department(id="wx", label="NOAA", channels=[make_channel("KHB60", 162.55, mode="NFM", id="w1")])
    system = System(id="s1", label="S", departments=[ham, air, bc, wx])
    return Catalog(favorites=[FavoritesList(
        id="f1", slug="flxx", favorite_key="FLXX", favorite_name="T", region="", counties="", scenario="",
        source_type="", system_or_category="", sites_or_coverage="", departments_or_channels="", mode="",
        monitorability="", upgrade_required="", source_url="", notes="", systems=[system])])


class TestBundle:
    def test_routing(self):
        resolved = resolve_plan(_scanner_plan(), _scanner_catalog())
        kinds = {route(c) for c in resolved.channels}
        assert kinds == {"channel", "am-air", "fm"}
        bundle = build_bundle(resolved)
        assert len(bundle.am_air) == 40 and len(bundle.fm) == 1
        assert all(c.mode != "AM" for c in bundle.channels)
        assert [z.name for z in bundle.am_zones] == ["Air Civil 01", "Air Civil 02"]
        assert len(bundle.am_zones[0].members) == AM_ZONE_MEMBER_MAX
        assert bundle.am_zones[0].scan_members == bundle.am_zones[0].members

    def test_zones_scan_lists_and_groups(self):
        bundle = build_bundle(resolve_plan(_scanner_plan(), _scanner_catalog()))
        assert [z.name for z in bundle.zones] == ["Ham 2m", "NOAA WX"]
        names = [s.name for s in bundle.scan_lists]
        assert names == ["Ham 2m", "Ham All", "Everything"]
        # NOAA is programmed but never in a scan list; broadcast is in the FM list only.
        noaa = next(c for c in bundle.channels if c.label == "KHB60")
        assert all(noaa not in s.members for s in bundle.scan_lists)
        assert bundle.scan_list_by_channel["Cougar WA1"] == "Ham 2m"
        assert noaa.name not in bundle.scan_list_by_channel

    def test_scan_lists_split_at_100(self):
        bundle = build_bundle(resolve_plan(_scanner_plan(), _scanner_catalog(n_ham=150)))
        assert [z.name for z in bundle.zones][:2] == ["Ham 2m 01", "Ham 2m 02"]
        assert all(len(s.members) <= 100 for s in bundle.scan_lists)
        assert [s.name for s in bundle.scan_lists if s.kind == "group"][:2] == ["Ham All 01", "Ham All 02"]
        assert len({s.name for s in bundle.scan_lists}) == len(bundle.scan_lists)

    def test_contacts_and_receive_groups(self):
        bundle = build_bundle(resolve_plan(_scanner_plan(), _scanner_catalog()))
        ids = {c.name: c.dmr_id for c in bundle.contacts}
        assert ids["Washington 1"] == 3153 and ids["King County"] == 333153 and ids["Simplex 99"] == 99
        groups = {g.name: [c.name for c in g.contacts] for g in bundle.rx_groups}
        assert groups == {"PNWDigital RX": ["Washington 1"], "SeattleDMR RX": ["King County"]}
        assert bundle.rx_group_by_channel["Cougar WA1"] == "PNWDigital RX"
        assert bundle.contact_by_channel["WW7PSR Seattle"] == "Simplex 99"
        assert any("placeholder DMR ID" in w for w in bundle.warnings)

    def test_bad_zone_name_is_rejected(self):
        bad = plan(PlanBlock("Ham", (ALL,), bank="Ham|Broken"))
        with pytest.raises(Atd890ExportError):
            build_bundle(resolve_plan(bad, make_catalog(make_channel("X", 146.52, mode="FM"))))


class TestCpsFiles:
    def test_header_and_template_shape(self):
        assert len(CHANNEL_HEADER) == 77 == len(CHANNEL_DEFAULTS)
        assert CHANNEL_HEADER[0] == "No." and CHANNEL_HEADER[-1] == "txcc"
        assert ZONE_HEADER[-1] == "Zone Hide " and AMZONE_HEADER[-1] == "Scan Channel "

    def _files(self):
        files, bundle = render_files(resolve_plan(_scanner_plan(), _scanner_catalog()))
        return files, bundle

    def test_every_field_quoted_crlf_ascii(self):
        files, _ = self._files()
        for name, text in files.items():
            assert "\r\n" in text and "\n" not in text.replace("\r\n", "")
            text.encode("ascii")
            if name.endswith(".CSV"):
                for line in text.rstrip("\r\n").split("\r\n"):
                    assert line.startswith('"') and line.endswith('"'), (name, line)

    def test_channel_rows(self):
        files, _ = self._files()
        rows = list(csv.reader(io.StringIO(files["Channel.CSV"])))
        assert rows[0] == list(CHANNEL_HEADER)
        assert all(len(r) == 77 for r in rows)
        by_name = {r[1]: r for r in rows[1:]}
        cougar = by_name["Cougar WA1"]
        assert cougar[2:6] == ["147.02000", "147.62000", "D-Digital", "High"]
        assert cougar[9:13] == ["Washington 1", "Group Call", "3153", "WA7DAM"]
        assert cougar[13] == "Same Color Code" and cougar[20] == "1" and cougar[21] == "1" and cougar[76] == "1"
        assert cougar[22] == "Ham 2m" and cougar[23] == "PNWDigital RX" and cougar[24] == "Off" and cougar[45] == "1"
        psrg = by_name["WW7PSR Seattle"]
        assert psrg[4] == "A-Analog" and psrg[6] == "25K" and psrg[7] == "Off" and psrg[8] == "103.5"
        assert psrg[3] == "146.36000" and psrg[24] == "Off"
        bare = by_name["Bare DMR"]
        # Receive-only DMR keeps the repeater input and repeater mode, PTT locked.
        assert bare[3] == "446.35000" and bare[24] == "On" and bare[45] == "1" and bare[5] == "Low"
        noaa = by_name["KHB60"]
        assert noaa[24] == "On" and noaa[22] == "None"
        assert [r[0] for r in rows[1:]] == [str(i) for i in range(1, len(rows))]

    def test_side_tables(self):
        files, _ = self._files()
        zones = list(csv.reader(io.StringIO(files["DMRZone.CSV"])))
        assert zones[0] == list(ZONE_HEADER)
        assert zones[1][1] == "Ham 2m" and zones[1][2].split("|")[0] == zones[1][5]
        assert zones[1][3].count("|") == zones[1][2].count("|") == zones[1][4].count("|")
        scans = list(csv.reader(io.StringIO(files["ScanList.CSV"])))
        assert scans[1][1] == "Ham 2m" and scans[1][-5:] == ["Selected", "0.5", "0.5", "0.1", "0.1"]
        am = list(csv.reader(io.StringIO(files["AMAir.CSV"])))
        assert am[1] == ["1", "118.3000", "Tower 0"]
        amz = list(csv.reader(io.StringIO(files["AMZone.CSV"])))
        assert amz[1][1] == "Air Civil 01" and amz[1][3] == "Tower 0"
        fm = list(csv.reader(io.StringIO(files["FM.CSV"])))
        assert fm[1] == ["1", "88.500", "Del", "KNKX"]
        tg = list(csv.reader(io.StringIO(files["DMRTalkGroups.CSV"])))
        assert tg[1][1:] == ["3153", "Washington 1", "Group Call", "None"]
        rid = list(csv.reader(io.StringIO(files["RadioIDList.CSV"])))
        assert rid[1] == ["1", "1", "WA7DAM"]
        rgl = list(csv.reader(io.StringIO(files["DMRReceiveGroupCallList.CSV"])))
        assert rgl[1] == ["1", "PNWDigital RX", "Washington 1", "3153"]
        manifest = files["atd890-test.LST"].split("\r\n")
        assert manifest[0] == "9" and manifest[1] == '0,"Channel.CSV"' and manifest[9] == '8,"AMZone.CSV"'

    def test_write_creates_directory_bundle(self, tmp_path):
        result = write_atd890(resolve_plan(_scanner_plan(), _scanner_catalog()), tmp_path / "bundle")
        assert (tmp_path / "bundle" / "Channel.CSV").is_file()
        assert len(result.files) == 10 and result.rows == 4 + 3 + 40 + 1 + 1
        target = get_target("atd890-cps")
        assert target.kind == "directory" and target.radio_id == "at-d890uv"
