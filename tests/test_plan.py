"""Channel-plan naming and resolution."""
import pytest

from wasds150.models.catalog import Catalog, Channel, Department, FavoritesList, System
from wasds150.models.plan import (
    SORT_NATURAL,
    TX_NONE,
    TX_REPEATER,
    TX_SIMPLEX,
    ChannelPlan,
    ChannelSelector,
    PlanBlock,
    natural_key,
)
from wasds150.plan.naming import NameAllocator, shorten_name
from wasds150.plan.resolve import resolve_mode, resolve_plan
from wasds150.radios.registry import SDS150, TD_H9


def make_channel(label, freq, **kwargs):
    return Channel(id=kwargs.pop("id", label.lower().replace(" ", "-")), label=label,
                   freq_mhz=freq, **kwargs)


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


def simple_plan(*blocks, radio_id="td-h9", reserve_slots=0):
    return ChannelPlan(id="test", radio_id=radio_id, label="Test",
                       blocks=tuple(blocks), reserve_slots=reserve_slots)


ALL = ChannelSelector(favorite_keys=("FLXX",))


class TestShortenName:
    def test_short_labels_pass_through(self):
        assert shorten_name("SAR1", 8) == "SAR1"

    def test_spaces_are_removed_to_gain_room(self):
        assert shorten_name("SAR 1", 8) == "SAR1"

    def test_result_never_exceeds_the_limit(self):
        for label in [
            "Olympic National Park Dispatch",
            "Clallam County Sheriff Primary Dispatch",
            "Quillayute River USCG Station Working",
            "NOAA Weather Radio KHB60 Seattle",
            "A" * 200,
        ]:
            assert len(shorten_name(label, 8)) <= 8

    def test_is_deterministic(self):
        assert shorten_name("Olympic National Park", 8) == shorten_name(
            "Olympic National Park", 8
        )

    def test_keeps_digits_that_identify_a_channel(self):
        assert "16" in shorten_name("Marine Channel 16", 8)

    @pytest.mark.parametrize(
        "label,fragment",
        [
            # The name is the only identification the radio displays, so the
            # distinguishing part of the label has to survive.
            ("Marine 16 Distress", "16"),
            ("Prince Rupert Traffic 74", "74"),
            ("ZSE Sector 03 Neah Bay", "03"),
            ("Seattle Traffic 5A", "5A"),
            ("NOAA Neah Bay KIH36", "KIH36"),
            ("W7FEL - Port Angeles", "W7FEL"),
            ("Ellis Mtn W7FEL", "W7FEL"),
            ("Mt Octopus K7PP", "K7PP"),
            ("GMRS RPT15", "RPT15"),
            ("WA SAR VSAR16", "VSAR16"),
        ],
    )
    def test_identifying_fragment_survives(self, label, fragment):
        assert fragment in shorten_name(label, 8)

    def test_uses_the_available_width(self):
        # Dropping a word and leaving the display half empty is a waste.
        assert shorten_name("USFS Air Guard", 8) == "USFSARGR"

    def test_similar_labels_stay_distinguishable(self):
        assert shorten_name("Striped Peak W7FEL", 8) != shorten_name(
            "Carlsborg W7FEL", 8
        )

    def test_charset_is_respected(self):
        assert shorten_name("A/B-C", 8, charset="ABC") == "ABC"

    def test_empty_label_falls_back(self):
        assert shorten_name("", 8) == "CH"

    def test_rejects_nonsense_limit(self):
        with pytest.raises(ValueError):
            shorten_name("x", 0)


class TestNameAllocator:
    def test_collisions_get_distinct_names(self):
        allocator = NameAllocator(8)
        first = allocator.allocate("Olympic National Park Dispatch")
        second = allocator.allocate("Olympic National Park Detail")
        assert first != second
        assert len(second) <= 8

    def test_same_key_returns_the_same_name(self):
        allocator = NameAllocator(8)
        assert allocator.allocate("Repeater", key="a") == allocator.allocate(
            "Repeater", key="a"
        )

    def test_many_collisions_stay_unique_and_in_bounds(self):
        allocator = NameAllocator(8)
        names = {allocator.allocate("Olympic National Forest") for _ in range(30)}
        assert len(names) == 30
        assert all(len(name) <= 8 for name in names)


class TestResolveMode:
    def test_supported_mode_is_kept(self):
        assert resolve_mode(make_channel("x", 146.52, mode="FM"), TD_H9) == "FM"

    def test_digital_modes_are_refused_not_coerced(self):
        for mode in ("P25", "DMR", "NXDN"):
            assert resolve_mode(make_channel("x", 155.0, mode=mode), TD_H9) is None

    def test_airband_is_inferred_as_am(self):
        assert resolve_mode(make_channel("x", 121.5, mode="AUTO"), TD_H9) == "AM"

    def test_amateur_band_is_inferred_as_wide_fm(self):
        assert resolve_mode(make_channel("x", 146.52), TD_H9) == "FM"

    def test_land_mobile_is_inferred_as_narrow(self):
        assert resolve_mode(make_channel("x", 155.16), TD_H9) == "NFM"


class TestResolvePlanFiltering:
    def test_out_of_band_channels_are_dropped_with_a_reason(self):
        catalog = make_catalog(
            make_channel("Keep Me", 155.16),
            make_channel("800 MHz Interop", 851.0125),
        )
        result = resolve_plan(simple_plan(PlanBlock("Test", (ALL,))), catalog)
        assert [c.label for c in result.channels] == ["Keep Me"]
        assert result.drop_reasons() == {"no-rx-coverage": 1}

    def test_talkgroups_are_dropped(self):
        catalog = make_catalog(
            Channel(id="tg", label="Dispatch TG", tgid=1001),
            make_channel("Conventional", 155.16),
        )
        result = resolve_plan(simple_plan(PlanBlock("Test", (ALL,))), catalog)
        assert result.drop_reasons() == {"not-conventional": 1}

    def test_duplicate_frequencies_take_one_slot(self):
        catalog = make_catalog(
            make_channel("SAR 1", 155.160, id="a"),
            make_channel("Search and Rescue 1", 155.160, id="b"),
        )
        result = resolve_plan(simple_plan(PlanBlock("Test", (ALL,))), catalog)
        assert result.slots_used == 1
        assert result.dropped[0].reason == "duplicate"
        assert "slot 1" in result.dropped[0].detail

    def test_avoided_channels_are_excluded_by_default(self):
        catalog = make_catalog(
            make_channel("Encrypted", 155.16, avoid=True),
            make_channel("Clear", 155.28),
        )
        result = resolve_plan(simple_plan(PlanBlock("Test", (ALL,))), catalog)
        assert [c.label for c in result.channels] == ["Clear"]

    def test_empty_selector_matches_nothing(self):
        catalog = make_catalog(make_channel("Anything", 155.16))
        result = resolve_plan(simple_plan(PlanBlock("Test", (ChannelSelector(),))), catalog)
        assert result.slots_used == 0


class TestResolvePlanCapacity:
    def _many(self, count):
        return make_catalog(
            *[make_channel(f"Ch {i}", 150.0 + i * 0.0125, id=f"c{i}") for i in range(count)]
        )

    def test_capacity_is_enforced(self):
        result = resolve_plan(simple_plan(PlanBlock("Test", (ALL,))), self._many(250))
        assert result.slots_used == 199
        assert result.drop_reasons()["capacity"] == 51

    def test_reserved_slots_are_held_back(self):
        plan = simple_plan(PlanBlock("Test", (ALL,)), reserve_slots=14)
        result = resolve_plan(plan, self._many(250))
        assert result.capacity == 185
        assert result.slots_used == 185

    def test_block_limit_caps_a_block(self):
        plan = simple_plan(PlanBlock("Test", (ALL,), limit=5))
        result = resolve_plan(plan, self._many(20))
        assert result.slots_used == 5
        assert result.block_counts == {"Test": 5}

    def test_slots_are_numbered_from_one_without_gaps(self):
        result = resolve_plan(simple_plan(PlanBlock("Test", (ALL,))), self._many(10))
        assert [c.slot for c in result.channels] == list(range(1, 11))

    def test_blocks_are_emitted_in_plan_order(self):
        catalog = make_catalog(
            make_channel("Alpha", 155.16), make_channel("Bravo", 462.5625)
        )
        plan = simple_plan(
            PlanBlock("Second", (ChannelSelector(freq_ranges=((400.0, 500.0),)),)),
            PlanBlock("First", (ChannelSelector(freq_ranges=((150.0, 160.0),)),)),
        )
        result = resolve_plan(plan, catalog)
        assert [c.label for c in result.channels] == ["Bravo", "Alpha"]


class TestNaturalSort:
    def test_numbers_sort_numerically_not_alphabetically(self):
        assert natural_key("GMRS 2") < natural_key("GMRS 15")

    def test_channel_numbers_beat_frequency_order(self):
        # GMRS main channels and the interstitials alternate in the band, so
        # a frequency sweep interleaves them as 15, 1, 16, 2 - unreadable on
        # a radio that shows one channel at a time.
        catalog = make_catalog(
            make_channel("GMRS 15", 462.5500, id="a"),
            make_channel("GMRS 1", 462.5625, id="b"),
            make_channel("GMRS 16", 462.5750, id="c"),
            make_channel("GMRS 2", 462.5875, id="d"),
        )
        plan = simple_plan(PlanBlock("G", (ALL,), sort=SORT_NATURAL))
        result = resolve_plan(plan, catalog)
        assert [c.label for c in result.channels] == [
            "GMRS 1", "GMRS 2", "GMRS 15", "GMRS 16",
        ]

    def test_suffixed_channels_stay_with_their_number(self):
        assert natural_key("Marine 21A") < natural_key("Marine 68")

    def test_sort_is_stable_for_labels_without_digits(self):
        catalog = make_catalog(
            make_channel("Zulu", 155.16, id="z"),
            make_channel("Alpha", 155.28, id="a"),
        )
        plan = simple_plan(PlanBlock("B", (ALL,), sort=SORT_NATURAL))
        result = resolve_plan(plan, catalog)
        assert [c.label for c in result.channels] == ["Alpha", "Zulu"]


class TestOzettePlanCompliance:
    """The shipped plan must not ask the radio to break a power limit."""

    def _resolved(self):
        from wasds150.catalog.baseline import load_baseline
        from wasds150.generate.pipeline import apply_profile
        from wasds150.models.catalog import Catalog
        from wasds150.models.profile import Profile
        from wasds150.plans import get_plan

        catalog = load_baseline()
        generated = apply_profile(
            catalog, Profile(based_on_catalog_hash=catalog.content_hash())
        )
        return resolve_plan(get_plan("h9-ozette"), Catalog(favorites=generated.enabled_favorites))

    def test_murs_stays_within_two_watts(self):
        for channel in self._resolved().channels:
            if channel.transmit and 151.8 <= channel.rx_freq_mhz <= 154.7:
                assert float(channel.power.rstrip("W")) <= 2.0, channel.label

    def test_gmrs_interstitials_stay_within_five_watts(self):
        # 47 CFR 95.1767 caps the 462 MHz interstitials at 5 W.
        interstitials = {462.5625, 462.5875, 462.6125, 462.6375, 462.6625,
                         462.6875, 462.7125}
        for channel in self._resolved().channels:
            if channel.transmit and round(channel.rx_freq_mhz, 4) in interstitials:
                assert float(channel.power.rstrip("W")) <= 5.0, channel.label

    def test_frs_only_channels_never_transmit(self):
        frs_only = {467.5625, 467.5875, 467.6125, 467.6375, 467.6625,
                    467.6875, 467.7125}
        for channel in self._resolved().channels:
            if round(channel.rx_freq_mhz, 4) in frs_only:
                assert not channel.transmit, channel.label

    def test_gmrs_channels_run_in_number_order(self):
        channels = self._resolved().channels
        gmrs = [c for c in channels if c.label.startswith("GMRS ") and "RPT" not in c.label]
        numbers = [int(c.label.split()[1]) for c in gmrs]
        assert numbers == sorted(numbers)


class TestTransmitPolicy:
    def test_receive_only_is_the_default(self):
        catalog = make_catalog(make_channel("Marine 16", 156.800))
        result = resolve_plan(simple_plan(PlanBlock("Marine", (ALL,))), catalog)
        assert result.channels[0].transmit is False
        assert result.channels[0].tx_freq_mhz is None

    def test_simplex_transmit_uses_the_receive_frequency(self):
        catalog = make_catalog(make_channel("Calling", 146.52, tone="TONE=C100"))
        plan = simple_plan(PlanBlock("Ham", (ALL,), tx_policy=TX_SIMPLEX))
        channel = resolve_plan(plan, catalog).channels[0]
        assert channel.transmit is True
        assert channel.tx_freq_mhz is None

    def test_repeater_transmit_uses_the_published_input(self):
        catalog = make_catalog(
            make_channel("Repeater", 146.96, tx_freq_mhz=146.36, tone="TONE=C103.5")
        )
        plan = simple_plan(PlanBlock("Ham", (ALL,), tx_policy=TX_REPEATER))
        channel = resolve_plan(plan, catalog).channels[0]
        assert channel.transmit is True
        assert channel.tx_freq_mhz == 146.36
        assert channel.tx_tone.ctcss_hz == 103.5

    def test_missing_repeater_input_is_not_invented(self):
        catalog = make_catalog(make_channel("Repeater", 146.96, tone="TONE=C103.5"))
        plan = simple_plan(PlanBlock("Ham", (ALL,), tx_policy=TX_REPEATER))
        result = resolve_plan(plan, catalog)
        assert result.channels[0].transmit is False
        assert any("receive-only" in w for w in result.warnings)

    def test_transmit_outside_hardware_coverage_is_refused(self):
        catalog = make_catalog(make_channel("Airband", 121.5, mode="AM"))
        plan = simple_plan(PlanBlock("Air", (ALL,), tx_policy=TX_SIMPLEX))
        result = resolve_plan(plan, catalog)
        assert result.channels[0].transmit is False

    def test_am_channels_are_always_receive_only(self):
        catalog = make_catalog(make_channel("Airband", 118.1, mode="AM"))
        plan = simple_plan(PlanBlock("Air", (ALL,), tx_policy=TX_SIMPLEX))
        result = resolve_plan(plan, catalog)
        assert result.channels[0].transmit is False
        assert any("receive-only" in w for w in result.warnings)

    def test_receive_squelch_is_left_open_on_monitoring_channels(self):
        catalog = make_catalog(make_channel("Dispatch", 155.16, tone="TONE=C127.3"))
        result = resolve_plan(simple_plan(PlanBlock("PS", (ALL,))), catalog)
        assert result.channels[0].rx_tone.kind == "none"
        assert result.channels[0].tx_tone.kind == "none"

    def test_digital_squelch_is_not_programmed_as_analog(self):
        catalog = make_catalog(
            make_channel("P25 Repeater", 146.96, tx_freq_mhz=146.36, tone="NAC=293")
        )
        plan = simple_plan(PlanBlock("Ham", (ALL,), tx_policy=TX_REPEATER))
        result = resolve_plan(plan, catalog)
        assert result.channels[0].tx_tone.kind == "none"
        assert any("not analog squelch" in w for w in result.warnings)


class TestUnverifiedProfile:
    def test_unverified_radio_warns_before_programming(self):
        catalog = make_catalog(make_channel("Ham", 146.52))
        result = resolve_plan(simple_plan(PlanBlock("A", (ALL,)), radio_id="ftx1"), catalog)
        assert any("unverified" in w for w in result.warnings)


class TestPlanValidation:
    def test_bad_tx_policy_is_rejected(self):
        with pytest.raises(ValueError, match="tx_policy"):
            PlanBlock("X", (ALL,), tx_policy="maybe")

    def test_duplicate_block_labels_are_rejected(self):
        with pytest.raises(ValueError, match="duplicate block"):
            simple_plan(PlanBlock("Same", (ALL,)), PlanBlock("Same", (ALL,)))

    def test_names_are_unique_across_the_whole_plan(self):
        catalog = make_catalog(
            *[
                make_channel("Olympic National Forest Net", 150.0 + i * 0.0125, id=f"c{i}")
                for i in range(12)
            ]
        )
        result = resolve_plan(simple_plan(PlanBlock("A", (ALL,))), catalog)
        names = [c.name for c in result.channels]
        assert len(set(names)) == len(names)
        assert all(len(n) <= 8 for n in names)
