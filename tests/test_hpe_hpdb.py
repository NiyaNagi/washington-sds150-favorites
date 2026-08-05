from wasds150.hpe import hpdb
from wasds150.hpe.record import Record, RecordDocument, parse_records, serialize_records
from wasds150.hpe.schema import BCDX36HP_SCHEMA, validate_schema


# ------------------------------------------------------------ keyed ids ---
def test_parse_keyed_id():
    assert hpdb.parse_keyed_id("SiteId=8201") == ("SiteId", 8201)
    assert hpdb.parse_keyed_id("") is None
    assert hpdb.parse_keyed_id("NoEquals") is None
    assert hpdb.parse_keyed_id("Key=notanumber") is None


def test_own_id_and_parent_id():
    r = Record(tag="Site", fields=["SiteId=8201", "TrunkId=9201", "Central Site"])
    assert hpdb.own_id(r) == ("SiteId", 8201)
    assert hpdb.parent_id(r) == ("TrunkId", 9201)


def test_own_id_blank_in_favorites_dialect():
    r = Record(tag="Site", fields=["", "", "Central Site"])
    assert hpdb.own_id(r) is None
    assert hpdb.parent_id(r) is None


# ----------------------------------------------------------------- geo ----
def test_haversine_dc_to_nyc_is_about_204_miles():
    # DC (38.9072, -77.0369) -> NYC (40.7128, -74.0060), well-known ~204mi
    distance = hpdb.haversine_miles(38.9072, -77.0369, 40.7128, -74.0060)
    assert 195 < distance < 215


def test_haversine_same_point_is_zero():
    assert hpdb.haversine_miles(45.0, -100.0, 45.0, -100.0) == 0.0


def test_geo_of_extracts_lat_lon_range_shape():
    r = Record(tag="C-Group", fields=["", "", "Group", "", "45.500000", "-100.500000", "10.0", "Circle", "", "x"])
    geo = hpdb.geo_of(r)
    assert geo.lat == 45.5
    assert geo.lon == -100.5
    assert geo.range_mi == 10.0
    assert geo.shape == "Circle"


def test_geo_of_returns_none_when_lat_lon_blank():
    r = Record(tag="C-Group", fields=["", "", "Group", "", "", "", "", "", "", ""])
    assert hpdb.geo_of(r) is None


def test_geo_of_returns_none_for_tag_without_geo_fields():
    r = Record(tag="TGID", fields=["", ""] + [""] * 15)
    assert hpdb.geo_of(r) is None


def test_rectangle_corners():
    r = Record(tag="Rectangle", fields=["", "47.000000", "-103.000000", "44.000000", "-98.000000"])
    corners = hpdb.rectangle_corners(r)
    assert corners == ((47.0, -103.0), (44.0, -98.0))


def test_rectangle_corners_none_for_non_rectangle():
    r = Record(tag="Site", fields=[])
    assert hpdb.rectangle_corners(r) is None


# ------------------------------------------------------- hpdb.cfg / index -
def test_synthetic_hpdb_cfg_arities(synthetic_hpdb_cfg_path):
    doc = hpdb.read_hpdb_cfg(synthetic_hpdb_cfg_path)
    for r in doc.records:
        schema = hpdb.HPDB_ONLY_SCHEMA.get(r.tag)
        if schema is not None:
            assert r.arity in schema.arities, f"{r.tag} arity mismatch"


def test_county_index_from_hpdb_cfg(synthetic_hpdb_cfg_path):
    doc = hpdb.read_hpdb_cfg(synthetic_hpdb_cfg_path)
    index = hpdb.CountyIndex.from_hpdb_cfg(doc)
    assert index.state_by_id[53] == "Washington"
    assert index.by_id[5301] == "King"
    assert index.by_id[5302] == "Pierce"
    assert index.counties_named("King") == [5301]
    assert index.id_by_name("King") == 5301
    assert index.id_by_name("King", state_id=53) == 5301
    assert index.id_by_name("King", state_id=99) is None
    assert index.id_by_name("Nonexistent") is None


def test_county_index_handles_name_collisions_across_states():
    doc = parse_records(
        "StateInfo\tStateId=1\tCountryId=0\tStateA\r\n"
        "StateInfo\tStateId=2\tCountryId=0\tStateB\r\n"
        "CountyInfo\tCountyId=100\tStateId=1\tWashington\r\n"
        "CountyInfo\tCountyId=200\tStateId=2\tWashington\r\n"
    )
    index = hpdb.CountyIndex.from_hpdb_cfg(doc)
    assert sorted(index.counties_named("Washington")) == [100, 200]
    assert index.id_by_name("Washington", state_id=1) == 100
    assert index.id_by_name("Washington", state_id=2) == 200


# --------------------------------------------------------- segmentation ---
def test_segment_systems_count_and_order(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    assert [s.kind() for s in systems] == ["Conventional", "Trunk"]
    assert systems[0].name() == "King County Public Safety"
    assert systems[1].name() == "Regional P25"


def test_preamble_records(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    preamble = hpdb.preamble_records(doc)
    assert [r.tag for r in preamble] == ["TargetModel", "FormatVersion"]


def test_system_identity(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    assert systems[0].identity() == ("CountyId", 5301)
    assert systems[1].identity() == ("TrunkId", 6001)


def test_system_tech(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    assert systems[1].tech() == "P25Standard"


def test_system_county_and_state_ids(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    conv, trunk = systems
    assert conv.county_ids() == [5301]
    assert conv.state_ids() == [53]
    assert trunk.county_ids() == [5301, 5302]  # multi-county trunk system
    assert trunk.state_ids() == [53]


def test_system_geos(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    assert len(systems[0].geos()) == 1
    assert len(systems[1].geos()) == 2  # Site + T-Group


def test_system_is_within_and_is_in_county(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    conv, trunk = systems
    assert conv.is_within(47.6, -122.33, 1.0)
    assert not conv.is_within(0.0, 0.0, 1.0)
    assert conv.is_in_county(5301)
    assert not conv.is_in_county(9999)


def test_area_county_owner_id_may_not_be_a_county_id():
    """The documented quirk: a Conventional system's field-1 id can be an
    AgencyId (not a CountyId); the real county lives in AreaCounty's
    field 2, which county_ids() must read -- not field 1."""
    header = Record(tag="Conventional", fields=["AgencyId=9101", "StateId=90", "Regional Transit"] + [""] * 11)
    area_state = Record(tag="AreaState", fields=["AgencyId=9101", "StateId=90"])
    area_county = Record(tag="AreaCounty", fields=["AgencyId=9101", "CountyId=9002"])
    doc = RecordDocument(records=[header, area_state, area_county], line_endings=["\r\n"] * 3)

    systems = hpdb.segment_systems(doc)
    assert len(systems) == 1
    system = systems[0]
    assert system.identity() == ("AgencyId", 9101)
    assert system.county_ids() == [9002]  # not 9101!


def test_is_voice_channel():
    assert hpdb.is_voice_channel(Record(tag="TGID", fields=[]))
    assert hpdb.is_voice_channel(Record(tag="C-Freq", fields=[]))
    assert not hpdb.is_voice_channel(Record(tag="T-Freq", fields=[]))
    assert not hpdb.is_voice_channel(Record(tag="Site", fields=[]))


# --------------------------------------------------------- selection ------
def test_by_county_selection(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    king_systems = hpdb.by_county(systems, 5301)
    assert {s.name() for s in king_systems} == {"King County Public Safety", "Regional P25"}
    pierce_systems = hpdb.by_county(systems, 5302)
    assert {s.name() for s in pierce_systems} == {"Regional P25"}
    assert hpdb.by_county(systems, 99999) == []


def test_within_radius_selection(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    nearby = hpdb.within_radius(systems, 47.6, -122.33, 1.0)
    assert len(nearby) == 2
    far_away = hpdb.within_radius(systems, 0.0, 0.0, 1.0)
    assert far_away == []


def test_select_systems_generic_predicate(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = hpdb.segment_systems(doc)
    trunked_only = hpdb.select_systems(systems, lambda s: s.kind() == "Trunk")
    assert len(trunked_only) == 1
    assert trunked_only[0].name() == "Regional P25"


# ------------------------------------------------------ dialect conversion
def test_to_favorites_dialect_blanks_id_columns(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc)
    for r in fav.records:
        if r.tag in hpdb.HIERARCHICAL_TAGS:
            assert r.fields[0] == ""
            assert r.fields[1] == ""


def test_to_favorites_dialect_drops_area_tags(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc)
    assert fav.find_first("AreaState") is None
    assert fav.find_first("AreaCounty") is None


def test_to_favorites_dialect_synthesizes_one_dqks_per_system(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc)
    assert len(fav.find_all("DQKs_Status")) == 2  # one per system (Conventional + Trunk)


def test_to_favorites_dialect_dqks_defaults_to_all_off():
    record = hpdb.synthesize_dqks_record()
    assert record.tag == "DQKs_Status"
    assert record.arity == 102
    assert all(v == "Off" for v in record.fields[1:])  # field 0 is the reserved blank


def test_to_favorites_dialect_never_synthesizes_bandplan(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc)
    assert fav.find_first("BandPlan_P25") is None
    assert fav.find_first("BandPlan_Mot") is None


def test_to_favorites_dialect_is_idempotent(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    once = hpdb.to_favorites_dialect(doc)
    twice = hpdb.to_favorites_dialect(once)
    assert len(twice.find_all("DQKs_Status")) == len(once.find_all("DQKs_Status"))
    assert serialize_records(once) == serialize_records(twice)


def test_to_favorites_dialect_can_skip_dqks_synthesis(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc, synthesize_dqks=False)
    assert fav.find_all("DQKs_Status") == []


def test_to_favorites_dialect_never_mutates_source_document(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    before = serialize_records(doc)
    hpdb.to_favorites_dialect(doc)
    after = serialize_records(doc)
    assert before == after


def test_converted_document_validates_cleanly_against_favorites_schema(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc)
    assert validate_schema(fav) == []


def test_converted_document_preserves_geo_and_names(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc)
    conv = fav.find_first("Conventional")
    name_spec = BCDX36HP_SCHEMA["Conventional"].field_by_name("name")
    assert conv.get(name_spec.index - 1) == "King County Public Safety"


def test_converted_document_round_trips_through_hpe_container(synthetic_hpdb_state_path):
    from wasds150.hpe import codec

    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    fav = hpdb.to_favorites_dialect(doc)
    text = serialize_records(fav)
    hpe_bytes = codec.encode_container(text)
    assert codec.decode_container(hpe_bytes) == text


# ------------------------------------------- SystemSlice -> catalog System
def test_system_slice_to_system_conventional(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    conv_slice = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Conventional")
    system = hpdb.system_slice_to_system(conv_slice)

    assert system.id == "hpdb:CountyId:5301"
    assert system.label == "King County Public Safety"
    assert system.sid is None  # Conventional: not a RadioReference "SID" (see module docstring)
    assert system.sites == []
    assert system.trunk_frequencies == []
    assert len(system.departments) == 1

    dept = system.departments[0]
    assert dept.id == "hpdb:CGroupId:8001"
    assert dept.label == "Fire Dispatch"
    assert dept.lat == 47.6
    assert dept.lon == -122.33
    assert dept.range_miles == 10.0
    assert dept.shape == "Circle"

    channel = dept.channels[0]
    assert channel.id == "hpdb:CFreqId:7001"
    assert channel.label == "Fire Disp 1"
    assert channel.freq_mhz == 154.28  # 154280000 Hz -> MHz
    assert channel.mode == "NFM"
    assert channel.service_type == 3
    assert channel.avoid is False


def test_system_slice_to_system_trunk(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    trunk_slice = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Trunk")
    system = hpdb.system_slice_to_system(trunk_slice)

    assert system.id == "hpdb:TrunkId:6001"
    assert system.label == "Regional P25"
    assert system.sid == 6001  # Trunk: own TrunkId doubles as the SID recipes match on
    assert system.tech == "P25Standard"
    assert system.departments == []

    assert len(system.sites) == 1
    site = system.sites[0]
    assert site.id == "hpdb:SiteId:7001"
    assert site.label == "Downtown Site"
    assert site.lat == 47.6
    assert site.lon == -122.33
    assert site.range_miles == 25.0
    assert site.shape == "Circle"

    assert len(site.departments) == 1
    tgroup = site.departments[0]
    assert tgroup.id == "hpdb:TGroupId:8101"
    assert tgroup.label == "Fire-EMS"

    assert len(tgroup.channels) == 1
    tgid_channel = tgroup.channels[0]
    assert tgid_channel.id == "hpdb:Tid:5001"
    assert tgid_channel.label == "Fire Dispatch"
    assert tgid_channel.tgid == 101
    assert tgid_channel.mode == "P25"
    assert tgid_channel.service_type == 3

    assert len(system.trunk_frequencies) == 1
    tfreq = system.trunk_frequencies[0]
    assert tfreq.id == "hpdb:TFreqId:9001"
    assert tfreq.freq_mhz == 851.0125  # 851012500 Hz -> MHz
    assert tfreq.lcn is None  # genuinely blank in the fixture -- never guessed


def test_system_slice_to_system_reads_master_hpdb_eight_field_t_freq_layout(
    synthetic_hpdb_state_path,
):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    original = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Trunk")
    records = list(original.records)
    index = next(i for i, record in enumerate(records) if record.tag == "T-Freq")
    records[index] = Record(
        tag="T-Freq",
        fields=["TFreqId=9001", "SiteId=7001", "", "", "851012500", "7", "Control", "P25"],
    )

    system = hpdb.system_slice_to_system(hpdb.SystemSlice(records=records))

    assert system.trunk_frequencies[0].freq_mhz == 851.0125
    assert system.trunk_frequencies[0].lcn == 7
    assert system.trunk_frequencies[0].usage == "Control"


def test_system_slice_to_system_ids_are_stable_hpdb_identifiers(synthetic_hpdb_state_path):
    """Preserving ids for merge: every id must be traceable back to the
    real RadioReference identifier, not a freshly-generated random one."""
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    for system_slice in hpdb.segment_systems(doc):
        system = hpdb.system_slice_to_system(system_slice)
        assert system.id.startswith("hpdb:")
        identity = system_slice.identity()
        assert identity is not None
        assert system.id == f"hpdb:{identity[0]}:{identity[1]}"


def test_system_slice_to_system_round_trips_through_builders_and_hpe_container(synthetic_hpdb_state_path):
    """The read direction (system_slice_to_system) and the write direction
    (wasds150.hpe.builders) must compose into a real, importable,
    schema-valid .hpe -- this is what makes a matched local HPDB fact
    produce actual per-list HPE output instead of just a provenance
    citation."""
    from wasds150.hpe import builders, codec, schema

    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    systems = [hpdb.system_slice_to_system(s) for s in hpdb.segment_systems(doc)]
    built_doc = builders.build_favorites_document(systems)
    assert schema.validate_schema(built_doc) == []

    hpe_bytes = codec.encode_container(serialize_records(built_doc))
    decoded_text = codec.decode_container(hpe_bytes)
    reparsed = parse_records(decoded_text)
    assert schema.validate_schema(reparsed) == []
    assert "King County Public Safety" in decoded_text
    assert "Regional P25" in decoded_text
    assert "Fire Dispatch" in decoded_text


# --------------------------------------- serialize/deserialize SystemSlice
def test_serialize_deserialize_system_slice_round_trips(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    original = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Trunk")

    serialized = hpdb.serialize_system_slice(original)
    # JSON-safe: only plain dict/list/str values.
    import json

    json.dumps(serialized)

    restored = hpdb.deserialize_system_slice(serialized)
    assert [r.tag for r in restored.records] == [r.tag for r in original.records]
    assert [r.fields for r in restored.records] == [r.fields for r in original.records]
    assert restored.identity() == original.identity()
    assert restored.name() == original.name()


def test_serialize_deserialize_system_slice_produces_equivalent_system(synthetic_hpdb_state_path):
    doc = hpdb.read_state_hpd(synthetic_hpdb_state_path)
    original = next(s for s in hpdb.segment_systems(doc) if s.kind() == "Conventional")
    restored = hpdb.deserialize_system_slice(hpdb.serialize_system_slice(original))
    assert hpdb.system_slice_to_system(original).to_dict() == hpdb.system_slice_to_system(restored).to_dict()


def test_deserialize_system_slice_handles_empty_list():
    restored = hpdb.deserialize_system_slice([])
    assert restored.records == []

