"""US amateur band plan, scan ranges and radio projection."""
import pytest

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.radios.bandplan import (
    BANDS,
    BANDS_BY_ID,
    CLASS_EXTRA,
    CLASS_GENERAL,
    all_calling_frequencies,
    band_for,
    general_class_summary,
    may_transmit,
)
from wasds150.radios.projection import project_favorites
from wasds150.radios.registry import FTX1, SDS150, TD_H9
from wasds150.radios.scan_ranges import ALL_RANGES, ranges_by_priority


class TestBandEdges:
    def test_every_band_is_well_formed(self):
        for band in BANDS:
            assert band.high_mhz > band.low_mhz, band.id
            for segment in band.license_segments:
                assert segment.high_mhz > segment.low_mhz, band.id
                assert band.low_mhz <= segment.low_mhz <= band.high_mhz, band.id
                assert band.low_mhz <= segment.high_mhz <= band.high_mhz, band.id

    def test_calling_frequencies_lie_inside_their_band(self):
        for band, calling in all_calling_frequencies():
            if band.id == "60m":
                # The four 60 m discrete channels are authorised separately
                # from the 5.3515-5.3665 band and genuinely sit outside it,
                # per 47 CFR 97.303(h)(3).
                continue
            assert band.low_mhz <= calling.mhz <= band.high_mhz, calling.label

    def test_sixty_metre_discrete_channels_sit_outside_the_band(self):
        band = BANDS_BY_ID["60m"]
        outside = [c for c in band.calling if not band.low_mhz <= c.mhz <= band.high_mhz]
        assert len(outside) == 4

    def test_band_lookup(self):
        assert band_for(14.2).id == "20m"
        assert band_for(146.52).id == "2m"
        assert band_for(500.0) is None


class TestGeneralClassPrivileges:
    @pytest.mark.parametrize(
        "mhz,allowed",
        [
            # 47 CFR 97.301(d). The Extra-only slivers are what make this
            # worth testing: they are easy to get wrong and illegal to.
            (1.850, True),
            (3.510, False),   # Extra only below 3.525
            (3.550, True),
            (3.700, False),   # Advanced and Extra only
            (3.900, True),
            (7.010, False),   # Extra only below 7.025
            (7.100, True),
            (7.150, False),   # Advanced and Extra only
            (7.200, True),
            (10.125, True),
            (14.010, False),  # Extra only below 14.025
            (14.100, True),
            (14.200, False),  # Advanced and Extra only
            (14.300, True),
            (21.010, False),
            (21.100, True),
            (21.250, False),  # Advanced and Extra only
            (21.300, True),
            (24.950, True),
            (28.500, True),
            (50.100, True),
            (146.520, True),
            (446.000, True),
        ],
    )
    def test_general_transmit_privileges(self, mhz, allowed):
        assert may_transmit(mhz, CLASS_GENERAL) is allowed

    def test_extra_has_everything_a_general_has(self):
        for band in BANDS:
            for segment in band.segments_for(CLASS_GENERAL):
                midpoint = (segment.low_mhz + segment.high_mhz) / 2
                assert may_transmit(midpoint, CLASS_EXTRA), band.id

    def test_summary_merges_adjacent_segments(self):
        assert general_class_summary(BANDS_BY_ID["10m"]) == "General: 28-29.7 MHz"

    def test_summary_reports_both_forty_metre_segments(self):
        summary = general_class_summary(BANDS_BY_ID["40m"])
        assert "7.025-7.125" in summary and "7.175-7.3" in summary


class TestModeRestrictions:
    def test_thirty_metres_forbids_phone(self):
        assert "No phone" in BANDS_BY_ID["30m"].prohibited

    def test_bands_with_a_phone_floor_say_so(self):
        for band_id in ("20m", "17m", "15m", "12m", "10m"):
            assert "No phone below" in BANDS_BY_ID[band_id].prohibited, band_id


class TestScanRanges:
    def test_ranges_are_well_formed(self):
        for scan_range in ALL_RANGES:
            assert scan_range.high_mhz > scan_range.low_mhz, scan_range.id
            assert scan_range.span_khz > 0

    def test_range_ids_are_unique(self):
        ids = [r.id for r in ALL_RANGES]
        assert len(set(ids)) == len(ids)

    def test_the_selection_fits_the_ftx1_pms_budget(self):
        # The FTX-1 has exactly 50 programmable scan pairs and no way to add
        # more, so the catalogue of ranges has to fit inside that budget.
        assert len(ranges_by_priority(50)) <= 50

    def test_selection_is_ordered_by_priority(self):
        selected = ranges_by_priority(10)
        assert selected == sorted(selected, key=lambda r: (r.priority, r.id))

    def test_no_range_covers_the_unreachable_band(self):
        # 222-225 MHz cannot be received by any radio in this project.
        for scan_range in ALL_RANGES:
            assert not (222.0 <= scan_range.low_mhz <= 225.0), scan_range.id

    def test_ham_ranges_stay_within_their_band(self):
        for scan_range in ALL_RANGES:
            band = BANDS_BY_ID.get(scan_range.band_id)
            if band is None:
                continue
            assert band.low_mhz <= scan_range.low_mhz, scan_range.id
            assert scan_range.high_mhz <= band.high_mhz, scan_range.id

    def test_every_ham_range_states_the_general_limits(self):
        for scan_range in ALL_RANGES:
            if scan_range.band_id in BANDS_BY_ID:
                assert "General" in scan_range.note, scan_range.id


def _list(*channels, reference_only=False):
    return FavoritesList(
        id="f", slug="x", favorite_key="X", favorite_name="X", region="", counties="",
        scenario="", source_type="", system_or_category="", sites_or_coverage="",
        departments_or_channels="", mode="", monitorability="", upgrade_required="",
        source_url="", notes="", reference_only=reference_only,
        systems=[System(id="s", label="S", departments=[
            Department(id="d", label="D", channels=list(channels))
        ])],
    )


class TestProjection:
    def test_reference_lists_are_pruned_to_the_target(self):
        favorites = [
            _list(
                Channel(id="a", label="HF", freq_mhz=14.074, mode="USB"),
                Channel(id="b", label="VHF", freq_mhz=155.16, mode="NFM"),
                reference_only=True,
            )
        ]
        result = project_favorites(favorites, SDS150)
        kept = [c.label for c in result.favorites[0].systems[0].departments[0].channels]
        assert kept == ["VHF"]
        assert result.dropped_channels == 1
        assert any("dropped" in w for w in result.warnings)

    def test_ordinary_lists_are_never_pruned(self):
        # Silently dropping from a normal list would hide the data errors the
        # HPE validator exists to catch.
        favorites = [_list(Channel(id="a", label="HF", freq_mhz=14.074, mode="USB"))]
        result = project_favorites(favorites, SDS150)
        assert len(result.favorites[0].systems[0].departments[0].channels) == 1
        assert result.dropped_channels == 0

    def test_projection_differs_per_radio(self):
        favorites = [
            _list(
                Channel(id="a", label="HF", freq_mhz=14.074, mode="USB"),
                Channel(id="b", label="2m", freq_mhz=146.52, mode="FM"),
                reference_only=True,
            )
        ]
        for profile, expected in ((SDS150, ["2m"]), (FTX1, ["HF", "2m"]), (TD_H9, ["2m"])):
            result = project_favorites(favorites, profile)
            kept = [
                c.label
                for c in result.favorites[0].systems[0].departments[0].channels
            ]
            assert kept == expected, profile.id

    def test_empty_departments_are_removed(self):
        favorites = [
            _list(Channel(id="a", label="HF", freq_mhz=14.074, mode="USB"), reference_only=True)
        ]
        result = project_favorites(favorites, SDS150)
        assert result.favorites[0].systems == []
        assert any("no channels are usable" in w for w in result.warnings)
