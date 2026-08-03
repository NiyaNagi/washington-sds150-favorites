"""End-to-end tests for the structured-generation pipeline this project's
audit identified as missing: a source's HPDB record tree -> a matched
recipe -> a structured FavoritesList -> a per-list .hpe -> decode/parse/
validate, plus the surrounding guarantees (determinism, actionable
missing-input warnings, no-private-input public lists, profile
customizations preserved through the same pipeline, and the installer
consuming generated output directly).
"""
from __future__ import annotations

from wasds150.bundle.hpe_export import build_per_list_hpe
from wasds150.catalog import baseline as catalog_baseline
from wasds150.generate.pipeline import apply_profile
from wasds150.hpe import codec, schema
from wasds150.hpe.record import parse_records
from wasds150.installer import paths as installer_paths
from wasds150.installer.confirm import confirm_phrase_for
from wasds150.installer.writer import write_favorites_list
from wasds150.models.catalog import Catalog, FavoritesList
from wasds150.models.profile import Profile
from wasds150.sources.sentinel_local import SentinelLocalSource
from wasds150.update.pipeline import build_and_merge, run_sources


def _trunked_row(slug="fltest", sid=6001, counties="Yakima") -> FavoritesList:
    # `counties` deliberately does NOT match the synthetic fixture's own
    # King/Pierce counties by default, so a plain SID-only match is
    # isolated for tests that want exactly one matched system; pass
    # counties="King" to also pull in the county-matched Conventional
    # system (see test_recipe_matches_multiple_systems_via_sid_and_county).
    return FavoritesList(
        id=slug,
        slug=slug,
        favorite_key="FLTEST",
        favorite_name="Test Regional P25",
        region="Statewide",
        counties=counties,
        scenario="Public safety",
        source_type="trunked P25 Phase II",
        system_or_category=f"Test Trunk SID {sid}",
        sites_or_coverage="",
        departments_or_channels="",
        mode="P25",
        monitorability="Full - unencrypted",
        upgrade_required="None",
        source_url="",
        notes="",
    )


def _hpdb_missing_row(slug="flmissing") -> FavoritesList:
    """A trunked row with no matching local data anywhere -- no SID text
    match, no free-text frequency, no seed -- so it must end up with
    zero systems and an actionable coverage warning."""
    return FavoritesList(
        id=slug,
        slug=slug,
        favorite_key="FLMISSING",
        favorite_name="Some Other Trunked System",
        region="Statewide",
        counties="Whatcom",
        scenario="Public safety",
        source_type="trunked P25 Phase II",
        system_or_category="Unmatched System SID 999999",
        sites_or_coverage="",
        departments_or_channels="Dispatch tac channel, no explicit frequency",
        mode="P25",
        monitorability="Mixed",
        upgrade_required="None",
        source_url="",
        notes="",
    )


def _public_freq_row(slug="flpublic") -> FavoritesList:
    """A conventional row with an explicit, already-checked-in literal
    frequency -- exactly the "no private input needed" shape."""
    return FavoritesList(
        id=slug,
        slug=slug,
        favorite_key="FLPUBLIC",
        favorite_name="Test Public Weather Channel",
        region="Statewide",
        counties="All 39 counties",
        scenario="Weather",
        source_type="conventional",
        system_or_category="Test NOAA transmitter",
        sites_or_coverage="Statewide",
        departments_or_channels="KTEST Seattle162.550",
        mode="WX",
        monitorability="Full - unencrypted",
        upgrade_required="None",
        source_url="https://www.weather.gov/nwr/",
        notes="",
    )


def _run_sentinel_pipeline(hpdb_cfg_path, base_catalog: Catalog, profile: Profile):
    source = SentinelLocalSource(hpdb_cfg_path=hpdb_cfg_path)
    run = run_sources([source])
    built = build_and_merge(base_catalog, profile, run.facts)
    return run, built


def _copy_synthetic_fixture(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    hpdb_dir = tmp_path / "copied_hpdb"
    hpdb_dir.mkdir()
    (hpdb_dir / "hpdb.cfg").write_bytes(synthetic_hpdb_cfg_path.read_bytes())
    (hpdb_dir / "s_000053.hpd").write_bytes(synthetic_hpdb_state_path.read_bytes())
    return hpdb_dir / "hpdb.cfg"


def make_simulated_card(tmp_path):
    card = tmp_path / "card"
    (card / installer_paths.FAVORITES_LISTS_DIR).mkdir(parents=True)
    (card / installer_paths.HPDB_DIR).mkdir(parents=True)
    return card


# ------- source HPDB record tree -> recipe -> structured FavoritesList ----
# -------------------------- -> per-list HPE -> decode/parse/validate -----
def test_hpdb_source_to_recipe_to_favorites_list_to_hpe_end_to_end(
    tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path
):
    hpdb_cfg_path = _copy_synthetic_fixture(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path)
    base_catalog = Catalog(favorites=[_trunked_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())

    run, built = _run_sentinel_pipeline(hpdb_cfg_path, base_catalog, profile)

    # 1. The source produced a real HPDB fact carrying its full record tree.
    assert run.outcomes[0].ok
    system_fact = next(f for f in run.facts if f.raw.get("sid") == 6001)
    assert "records" in system_fact.raw

    # 2. The recipe matched it (by SID, extracted from the row's own text).
    coverage = next(c for c in built["coverage"] if c.slug == "fltest")
    assert coverage.status == "full"

    # 3. The merged catalog's row now has a real, populated System -- not
    #    just a provenance citation.
    merged_fl = built["merge"].merged_catalog.by_slug("fltest")
    assert merged_fl is not None
    assert len(merged_fl.systems) == 1
    system = merged_fl.systems[0]
    assert system.label == "Regional P25"
    assert system.sid == 6001
    assert system.sites[0].departments[0].channels[0].tgid == 101

    # 4. Generating from this merged catalog produces a real per-list .hpe.
    result = apply_profile(built["merge"].merged_catalog, profile)
    export = build_per_list_hpe(result.enabled_favorites)
    assert export.warnings == []
    assert set(export.files) == {"FLTEST.hpe"}

    # 5. Decode/parse/validate before trusting it.
    hpe_bytes = export.files["FLTEST.hpe"]
    text = codec.decode_container(hpe_bytes)
    doc = parse_records(text)
    assert schema.validate_schema(doc) == []
    assert "Regional P25" in text
    assert "Fire Dispatch" in text
    assert codec.has_signature_line(text)


def test_recipe_matches_multiple_systems_via_sid_and_county(
    tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path
):
    """"Multiple systems may populate one Favorites List": a recipe that
    matches both by SID (the Trunk system) and by county (the
    Conventional system covering that same county) ends up with both,
    deduplicated and in a stable order."""
    hpdb_cfg_path = _copy_synthetic_fixture(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path)
    base_catalog = Catalog(favorites=[_trunked_row(counties="King")])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())

    _, built = _run_sentinel_pipeline(hpdb_cfg_path, base_catalog, profile)
    merged_fl = built["merge"].merged_catalog.by_slug("fltest")

    assert len(merged_fl.systems) == 2
    labels = {s.label for s in merged_fl.systems}
    assert labels == {"Regional P25", "King County Public Safety"}

    # Re-running enrichment again must not duplicate either system.
    rerun_facts = run_sources([SentinelLocalSource(hpdb_cfg_path=hpdb_cfg_path)]).facts
    built_again = build_and_merge(base_catalog, profile, rerun_facts)
    assert len(built_again["merge"].merged_catalog.by_slug("fltest").systems) == 2


# ----------------------------------------------------- deterministic rerun
def test_full_pipeline_is_deterministic_across_independent_runs(
    tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path
):
    hpdb_cfg_path = _copy_synthetic_fixture(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path)
    base_catalog = Catalog(favorites=[_trunked_row(), _public_freq_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())

    def _run_once():
        _, built = _run_sentinel_pipeline(hpdb_cfg_path, base_catalog, profile)
        result = apply_profile(built["merge"].merged_catalog, profile)
        export = build_per_list_hpe(result.enabled_favorites)
        return result, export

    result1, export1 = _run_once()
    result2, export2 = _run_once()

    assert result1.content_hash == result2.content_hash
    assert export1.warnings == export2.warnings
    assert set(export1.files) == set(export2.files)
    for name in export1.files:
        assert export1.files[name] == export2.files[name]  # byte-identical .hpe


# --------------------------------------------------- missing-input warning
def test_missing_local_input_produces_actionable_warning_not_empty_success():
    base_catalog = Catalog(favorites=[_hpdb_missing_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())

    # No sources run at all (simulates "nothing configured").
    built = build_and_merge(base_catalog, profile, facts=[])
    coverage = next(c for c in built["coverage"] if c.slug == "flmissing")
    assert coverage.status == "none"
    assert coverage.warnings
    assert "HPDB" in coverage.warnings[0] or "RadioReference" in coverage.warnings[0]

    result = apply_profile(built["merge"].merged_catalog, profile)
    generated = next(f for f in result.favorites if f.slug == "flmissing")
    assert generated.systems == []

    export = build_per_list_hpe(result.enabled_favorites)
    assert export.files == {}
    assert len(export.warnings) == 1
    assert "FLMISSING" in export.warnings[0]
    assert "Some Other Trunked System" in export.warnings[0]
    # Actionable: names what to do next, not just "empty".
    assert "sources configure" in export.warnings[0] or "sources update" in export.warnings[0]


# ------------------------------------------------- public static-frequency
def test_public_static_frequency_list_needs_no_local_input_at_all():
    """A conventional row with an explicit literal frequency already
    checked into its own text must produce a real, importable .hpe with
    zero sources run, zero HPDB, zero network."""
    base_catalog = Catalog(favorites=[_public_freq_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())

    result = apply_profile(base_catalog, profile)
    fl = next(f for f in result.favorites if f.slug == "flpublic")
    assert len(fl.systems) == 1
    channel = fl.systems[0].departments[0].channels[0]
    assert channel.freq_mhz == 162.55

    export = build_per_list_hpe(result.enabled_favorites)
    assert export.warnings == []
    assert set(export.files) == {"FLPUBLIC.hpe"}
    text = codec.decode_container(export.files["FLPUBLIC.hpe"])
    assert schema.validate_schema(parse_records(text)) == []


def test_real_baseline_no_private_input_categories_produce_real_hpe():
    """The same guarantee against the real shipped 78-row baseline, for
    the specific categories the audit called out by name: NOAA weather,
    national interoperability, FRS/GMRS, marine VHF, aviation/guard."""
    catalog = catalog_baseline.load_baseline()
    profile = Profile(based_on_catalog_hash=catalog.content_hash())
    result = apply_profile(catalog, profile)
    export = build_per_list_hpe(result.enabled_favorites)

    for key in ("FL75", "FL02", "FL65", "FL52", "FL48"):
        assert key + ".hpe" in export.files, f"{key} should have a real .hpe with no private input"
        text = codec.decode_container(export.files[key + ".hpe"])
        assert schema.validate_schema(parse_records(text)) == []


# ------------------------------------------ profile customizations preserved
def test_profile_customizations_survive_alongside_populated_systems(
    tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path
):
    hpdb_cfg_path = _copy_synthetic_fixture(tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path)
    base_catalog = Catalog(favorites=[_trunked_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())
    profile.set_override("fltest", "notes", "My custom field note")
    profile.set_override("fltest", "favorite_name", "My Renamed List")

    _, built = _run_sentinel_pipeline(hpdb_cfg_path, base_catalog, profile)
    result = apply_profile(built["merge"].merged_catalog, profile)
    fl = next(f for f in result.favorites if f.slug == "fltest")

    # The user's presentation overrides are exactly as they set them...
    assert fl.notes == "My custom field note"
    assert fl.favorite_name == "My Renamed List"
    # ...and the matched local HPDB system is *also* present, unharmed by
    # the override.
    assert len(fl.systems) == 1
    assert fl.systems[0].label == "Regional P25"

    # The generated .hpe reflects the override too (system label follows
    # favorite_name).
    export = build_per_list_hpe(result.enabled_favorites)
    assert export.warnings == []
    text = codec.decode_container(export.files["FLTEST.hpe"])
    assert "Regional P25" in text  # the HPDB system's own name is untouched


def test_profile_disable_excludes_row_from_hpe_export_but_keeps_systems_data():
    base_catalog = Catalog(favorites=[_public_freq_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())
    profile.set_enabled("flpublic", False)

    result = apply_profile(base_catalog, profile)
    disabled_fl = next(f for f in result.favorites if f.slug == "flpublic")
    assert disabled_fl.enabled is False
    assert disabled_fl.systems  # still computed even though disabled

    export = build_per_list_hpe(result.enabled_favorites)  # enabled_favorites excludes it
    assert export.files == {}
    assert export.warnings == []  # disabled, not "missing" -- no warning needed


# --------------------------------------------- installer consumes generated
def test_installer_consumes_generated_favorites_list_directly(tmp_path):
    """The default install workflow: profile -> generated favorites ->
    install, with no hand-authored Systems JSON anywhere in the path."""
    base_catalog = Catalog(favorites=[_public_freq_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())
    result = apply_profile(base_catalog, profile)
    fl = next(f for f in result.favorites if f.slug == "flpublic")
    assert fl.systems  # precondition: this is what makes install possible

    from wasds150.hpe import builders

    doc = builders.build_favorites_document(fl.systems)

    card = make_simulated_card(tmp_path)
    write_result = write_favorites_list(
        card,
        index=7,
        document=doc,
        user_name=fl.favorite_name,
        backup_dir=tmp_path / "backups",
        confirm_phrase=confirm_phrase_for(card),
        dry_run=False,
    )

    assert write_result.verified
    assert write_result.backup_path is not None and write_result.backup_path.exists()
    hpd_path = card / installer_paths.FAVORITES_LISTS_DIR / "f_000007.hpd"
    assert hpd_path.exists()
    assert b"KTEST Seattle" in hpd_path.read_bytes()
    # Safety controls remain fully in force: HPDB is still never touched.
    assert not installer_paths.is_within_allowed_write_path(card, card / installer_paths.HPDB_DIR / "hpdb.cfg")


def test_installer_dry_run_does_not_write_when_generated_list_is_empty(tmp_path):
    """A row with no systems should never even reach the installer with a
    plausible-looking (but actually empty) document -- callers are
    expected to check ``fl.systems`` first (as the CLI/API do), but even
    if an empty System list is passed through, no channels are written."""
    base_catalog = Catalog(favorites=[_hpdb_missing_row()])
    profile = Profile(based_on_catalog_hash=base_catalog.content_hash())
    result = apply_profile(base_catalog, profile)
    fl = next(f for f in result.favorites if f.slug == "flmissing")
    assert fl.systems == []
