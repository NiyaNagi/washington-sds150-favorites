from wasds150.hpe import builders, codec, schema
from wasds150.hpe.record import parse_records, serialize_records
from wasds150.models.catalog import Channel, Department, FavoritesList, Site, System, TrunkFrequency


def test_build_conventional_records_valid_arity_and_content():
    system = System(
        id="s1",
        label="County PS",
        departments=[
            Department(
                id="d1",
                label="Dispatch",
                channels=[
                    Channel(id="c1", label="Fire", freq_mhz=154.28, mode="NFM", tone="D023", service_type=3, priority=True),
                ],
            )
        ],
    )
    records = builders.build_conventional_records(system)
    assert [r.tag for r in records] == ["Conventional", "C-Group", "C-Freq"]
    for r in records:
        assert r.arity in schema.BCDX36HP_SCHEMA[r.tag].arities

    conv, group, freq = records
    assert conv.get(schema.BCDX36HP_SCHEMA["Conventional"].field_by_name("name").index - 1) == "County PS"
    assert group.get(schema.BCDX36HP_SCHEMA["C-Group"].field_by_name("name").index - 1) == "Dispatch"
    freq_schema = schema.BCDX36HP_SCHEMA["C-Freq"]
    assert freq.get(freq_schema.field_by_name("name").index - 1) == "Fire"
    assert freq.get(freq_schema.field_by_name("freq_hz").index - 1) == "154280000"
    assert freq.get(freq_schema.field_by_name("tone").index - 1) == "D023"
    assert freq.get(freq_schema.field_by_name("service_type").index - 1) == "3"
    assert freq.get(freq_schema.field_by_name("priority").index - 1) == "On"


def test_avoid_flag_renders_blank_when_unset_and_on_when_set():
    ch_normal = Channel(id="c1", label="A", freq_mhz=100.0, avoid=False)
    ch_avoided = Channel(id="c2", label="B", freq_mhz=100.0, avoid=True)
    r1 = builders.build_c_freq_record(ch_normal)
    r2 = builders.build_c_freq_record(ch_avoided)
    avoid_idx = schema.BCDX36HP_SCHEMA["C-Freq"].field_by_name("avoid").index - 1
    assert r1.fields[avoid_idx] == ""
    assert r2.fields[avoid_idx] == "On"


def test_build_trunk_records_with_sites_and_t_freq():
    system = System(
        id="s2",
        label="Statewide P25",
        sid=1234,
        wacn="ABCDE",
        tech="P25Standard",
        sites=[
            Site(
                id="site1",
                label="Main",
                lat=45.5,
                lon=-100.5,
                range_miles=25,
                shape="Circle",
                departments=[
                    Department(
                        id="d1",
                        label="Fire-EMS",
                        channels=[Channel(id="c1", label="Fire Disp", tgid=101, mode="P25", service_type=3)],
                    )
                ],
            )
        ],
        trunk_frequencies=[TrunkFrequency(id="tf1", freq_mhz=851.0125, lcn=1, usage="Control")],
    )
    records = builders.build_trunk_records(system)
    tags = [r.tag for r in records]
    assert tags == ["Trunk", "Site", "T-Group", "TGID", "T-Freq"]
    for r in records:
        assert r.arity in schema.BCDX36HP_SCHEMA[r.tag].arities


def test_t_freq_preserves_lcn_verbatim_including_zero():
    tf_zero = TrunkFrequency(id="tf1", freq_mhz=851.0, lcn=0, usage="Control")
    tf_none = TrunkFrequency(id="tf2", freq_mhz=851.5, lcn=None)
    r_zero = builders.build_t_freq_record(tf_zero)
    r_none = builders.build_t_freq_record(tf_none)
    lcn_idx = schema.BCDX36HP_SCHEMA["T-Freq"].field_by_name("lcn").index - 1
    assert r_zero.fields[lcn_idx] == "0"  # not force-zeroed and not blanked
    assert r_none.fields[lcn_idx] == ""  # genuinely unknown -> blank, never guessed


def test_is_trunked_detection():
    conv = System(id="s1", label="Conv")
    trunk_by_sid = System(id="s2", label="Trunk", sid=1)
    trunk_by_site = System(id="s3", label="Trunk", sites=[Site(id="x", label="Site")])
    assert not builders.is_trunked(conv)
    assert builders.is_trunked(trunk_by_sid)
    assert builders.is_trunked(trunk_by_site)


def test_build_system_records_dispatches_correctly():
    conv = System(id="s1", label="Conv", departments=[Department(id="d1", label="G", channels=[])])
    trunk = System(id="s2", label="Trunk", sid=99)
    assert builders.build_system_records(conv)[0].tag == "Conventional"
    assert builders.build_system_records(trunk)[0].tag == "Trunk"


def test_build_favorites_document_has_header_and_signature():
    system = System(id="s1", label="Conv", departments=[])
    doc = builders.build_favorites_document([system])
    assert doc.records[0].tag == "TargetModel"
    assert doc.records[0].fields == ["BCDx36HP"]
    assert doc.records[1].tag == "FormatVersion"
    assert doc.records[1].fields == ["1.00"]
    assert doc.records[-1].tag == "File"
    assert doc.records[-1].fields == ["HomePatrol Export File"]
    assert all(ending == "\r\n" for ending in doc.line_endings)


def test_built_document_validates_cleanly_against_schema():
    system = System(
        id="s1",
        label="Conv",
        departments=[Department(id="d1", label="Ops", channels=[Channel(id="c1", label="Ch1", freq_mhz=154.1, mode="NFM")])],
    )
    doc = builders.build_favorites_document([system])
    assert schema.validate_schema(doc) == []


def test_built_document_round_trips_through_hpe_container():
    system = System(
        id="s1",
        label="Conv",
        departments=[Department(id="d1", label="Ops", channels=[Channel(id="c1", label="Ch1", freq_mhz=154.1, mode="NFM")])],
    )
    doc = builders.build_favorites_document([system])
    text = serialize_records(doc)
    hpe_bytes = codec.encode_container(text)
    decoded_text = codec.decode_container(hpe_bytes)
    assert decoded_text == text
    reparsed = parse_records(decoded_text)
    assert [r.tag for r in reparsed.records] == [r.tag for r in doc.records]


def test_build_favorites_list_hpe_convenience_function():
    system = System(
        id="s1",
        label="Conv",
        departments=[
            Department(
                id="d1",
                label="Ops",
                channels=[Channel(id="c1", label="Channel", freq_mhz=154.1, mode="NFM")],
            )
        ],
    )
    fl = FavoritesList(
        id="fl1", slug="fl1", favorite_key="FL01", favorite_name="Test", region="", counties="",
        scenario="", source_type="", system_or_category="", sites_or_coverage="",
        departments_or_channels="", mode="", monitorability="", upgrade_required="", source_url="",
        notes="", systems=[system],
    )
    hpe_bytes = builders.build_favorites_list_hpe(fl)
    text = codec.decode_container(hpe_bytes)
    assert "Conv" in text
