import base64
import json
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

from wasds150.appctx import build_context
from wasds150.config import AppConfig
from wasds150.models.catalog import Channel, Department, Site, System, TrunkFrequency
from wasds150.models.provenance import Provenance
from wasds150.webui.server import build_server


@pytest.fixture()
def live_server(tmp_path, sample_csv_path):
    config = AppConfig(home=tmp_path / "home")
    config.ensure_dirs()
    ctx = build_context(config, csv_override=sample_csv_path)
    server, token = build_server(ctx, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[0], server.server_address[1]
    base_url = f"http://{host}:{port}"
    try:
        yield base_url, token, ctx
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _request(base_url, path, token=None, method="GET", body=None):
    url = base_url + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if token is not None:
        req.add_header("X-Wasds150-Token", token)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read(), dict(e.headers)


def test_index_page_served_with_token_embedded(live_server):
    base_url, token, ctx = live_server
    status, body, _ = _request(base_url, "/")
    assert status == 200
    assert token.encode("ascii") in body
    assert b"__WASDS150_TOKEN__" not in body


def test_static_js_and_css_served(live_server):
    base_url, _, _ = live_server
    status, body, headers = _request(base_url, "/app.js")
    assert status == 200
    assert headers["Content-Type"].startswith("application/javascript")

    status, body, headers = _request(base_url, "/styles.css")
    assert status == 200
    assert headers["Content-Type"].startswith("text/css")


def test_static_path_traversal_blocked(live_server):
    base_url, _, _ = live_server
    status, _, _ = _request(base_url, "/../cli.py")
    assert status == 404


def test_api_requires_token(live_server):
    base_url, _, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/dashboard")
    assert status == 401


def test_api_rejects_wrong_token(live_server):
    base_url, _, _ = live_server
    status, _, _ = _request(base_url, "/api/v1/dashboard", token="wrong-token")
    assert status == 401


def test_dashboard_endpoint(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/dashboard", token=token)
    assert status == 200
    data = json.loads(body)
    assert data["counts"]["baseline_total"] == 3


def test_catalog_endpoint_and_filter(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/catalog", token=token)
    data = json.loads(body)
    assert len(data["favorites"]) == 3
    assert "systems" in data["favorites"][0]
    assert "provenance" in data["favorites"][0]
    assert "profile_state" in data["favorites"][0]

    status, body, _ = _request(base_url, "/api/v1/catalog-summaries", token=token)
    data = json.loads(body)
    assert data["total"] == 3
    assert "systems" not in data["favorites"][0]
    assert "provenance" not in data["favorites"][0]

    status, body, _ = _request(base_url, "/api/v1/catalog-summaries?region=Eastern", token=token)
    data = json.loads(body)
    assert len(data["favorites"]) == 1
    assert data["favorites"][0]["slug"] == "fl09a"


def test_catalog_entry_returns_all_nested_metadata_and_profile_state(live_server):
    base_url, token, ctx = live_server
    favorite = ctx.catalog.by_slug("fl01")
    favorite.systems = [System(
        id="system-1", label="Regional", sid=101, wacn="BEE00", tech="P25", avoid=True,
        trunk_frequencies=[TrunkFrequency(id="frequency-1", freq_mhz=851.0125, lcn=7, usage="Control")],
        sites=[Site(
            id="site-1", label="Central", lat=47.5, lon=-122.3, range_miles=25.0,
            shape="Circle", avoid=False,
            departments=[Department(
                id="department-1", label="Operations", encrypted_bucket=True, dqk=3,
                lat=47.5, lon=-122.3, range_miles=10.0, shape="Circle", avoid=True,
                channels=[Channel(
                    id="channel-1", label="Dispatch", tgid=123, mode="P25", notes="Test",
                    tone="NAC=123", service_type=3, priority=True, avoid=True,
                )],
            )],
        )],
    )]
    favorite.provenance = [Provenance(
        source_adapter="synthetic", source_url="https://example.invalid/source",
        fetched_at="2026-08-04T00:00:00+00:00", confidence="verified",
    )]
    profile = ctx.load_profile()
    profile.set_enabled("fl01", False)
    profile.set_override("fl01", "notes", "Local note")
    profile.save(ctx.config.profile_path)

    status, body, _ = _request(base_url, "/api/v1/catalog/fl01", token=token)

    assert status == 200
    data = json.loads(body)
    assert data["systems"][0]["sites"][0]["departments"][0]["channels"][0]["tgid"] == 123
    assert data["systems"][0]["trunk_frequencies"][0]["lcn"] == 7
    assert data["provenance"][0]["confidence"] == "verified"
    assert data["profile_state"]["effective_enabled"] is False
    assert data["profile_state"]["overrides"] == {"notes": "(private override value hidden)"}


def test_catalog_metadata_redacts_credentials_queries_and_local_paths(live_server):
    base_url, token, ctx = live_server
    favorite = ctx.catalog.by_slug("fl01")
    favorite.source_url = "https://user:secret@example.invalid/data?token=private#fragment"
    favorite.provenance = [
        Provenance(
            source_adapter="local", source_url="file:///C:/private/hpdb.cfg",
            confidence="verified",
        ),
        Provenance(
            source_adapter="legacy", source_url="ftp://user:secret@example.invalid/private",
            confidence="community",
        ),
        Provenance(
            source_adapter="malicious", source_url="catalog://user:secret@host/private?token=secret",
            confidence="community",
        ),
    ]
    profile = ctx.load_profile()
    profile.set_override("fl01", "source_url", "C:\\private\\export.csv")
    profile.entry_for("fl01").note = "password=do-not-return"
    profile.save(ctx.config.profile_path)

    status, body, _ = _request(base_url, "/api/v1/catalog/fl01", token=token)

    assert status == 200
    payload = body.decode("utf-8")
    data = json.loads(body)
    assert data["source_url"] == "https://example.invalid/data"
    assert data["provenance"][0]["source_url"] == "(local path redacted)"
    assert data["provenance"][1]["source_url"] == "(unsupported source reference redacted)"
    assert data["provenance"][2]["source_url"] == "(unsupported source reference redacted)"
    assert data["profile_state"]["overrides"]["source_url"] == "(local path redacted)"
    assert data["profile_state"]["note_present"] is True
    assert "secret" not in payload
    assert "private" not in payload
    assert "do-not-return" not in payload


def test_catalog_entry_not_found(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/catalog/nope", token=token)
    assert status == 404


def test_sentinel_workspace_discovery_and_bulk_plan_endpoints(live_server, tmp_path):
    base_url, token, _ = live_server
    workspace = tmp_path / "Uniden" / "BCDx36HP"
    favorites = workspace / "FavoriteLists"
    profile = workspace / "Profile" / "Preset"
    favorites.mkdir(parents=True)
    profile.mkdir(parents=True)
    index = "TargetModel\tBCDx36HP\r\nFormatVersion\t1.00\r\n"
    (favorites / "f_list.cfg").write_bytes(index.encode("ascii"))
    (profile / "f_list.cfg").write_bytes(index.encode("ascii"))
    (profile / "profile.cfg").write_bytes(b"profile")

    query = urllib.parse.urlencode({"path": str(workspace)})
    status, body, _ = _request(base_url, f"/api/v1/sentinel/workspace?{query}", token=token)
    assert status == 200
    discovered = json.loads(body)
    assert discovered["exists"] is True
    assert discovered["profiles"] == ["Preset"]

    status, body, _ = _request(
        base_url,
        "/api/v1/sentinel/install",
        token=token,
        method="POST",
        body={
            "workspace": str(workspace),
            "profile_name": "Preset",
            "backup_dir": str(tmp_path / "backups"),
            "slugs": ["fl01"],
        },
    )
    assert status == 200
    plan = json.loads(body)
    assert plan["dry_run"] is True
    assert plan["confirmation_phrase"] == "IMPORT Preset"
    assert len(plan["assignments"]) == 1
    assert not (tmp_path / "backups").exists()


def test_display_palette_endpoints(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/display/palettes", token=token)
    assert status == 200
    data = json.loads(body)
    assert len(data["palettes"]) >= 4
    assert data["screens"] == [
        "SimpleConventional", "SimpleTrunk", "DetailConventional",
        "DetailTrunk", "Search", "Weather", "Tone out",
    ]
    assert all(palette["minimum_contrast"] >= 4.5 for palette in data["palettes"])
    assert len(data["supported_colors"]) == 147
    assert data["supported_colors"][0] == {"index": 0, "name": "AliceBlue", "value": "EFF7FF"}

    palette_id = data["palettes"][0]["id"]
    status, body, headers = _request(base_url, f"/api/v1/display/palettes/{palette_id}", token=token)
    assert status == 200
    assert body.startswith(b"<?xml")
    assert b'<UndienScanner Model="SDS100" FileType="DisplayCustomizer">' in body
    assert headers["Content-Type"].startswith("application/xml")
    assert headers["Content-Disposition"].endswith(f'wasds150-display-{palette_id}.xml"')

    status, _, _ = _request(base_url, "/api/v1/display/palettes/nope", token=token)
    assert status == 404

    custom = {
        "name": "API Custom",
        "colors": data["palettes"][0]["colors"],
        "global_item_colors": {"Func": {"text": "EFF7FF", "back": "000000"}},
        "screen_item_colors": {"SimpleTrunk||0": {"text": "F7EBD6", "back": "000084"}},
        "global_item_options": {"Option_3": "Time"},
        "screen_item_options": {"SimpleTrunk||3": "GPS"},
    }
    status, body, headers = _request(
        base_url, "/api/v1/display/custom", token=token, method="POST", body=custom,
    )
    assert status == 200
    assert b'Text="EFF7FF" Back="000000"' in body
    assert b'Text="F7EBD6" Back="000084"' in body
    import xml.etree.ElementTree as ET
    custom_root = ET.fromstring(body)
    custom_option = custom_root.find("./Screen[@Name='SimpleTrunk']/Item[@Name='Option_3']")
    assert custom_option.attrib["Option"] == "GPS"
    assert headers["Content-Type"].startswith("application/xml")

    status, _, _ = _request(
        base_url, "/api/v1/display/custom", token=token, method="POST", body=[],
    )
    assert status == 400

    custom["colors"]["system"] = "ABCDEF"
    status, body, _ = _request(
        base_url, "/api/v1/display/custom", token=token, method="POST", body=custom,
    )
    assert status == 400
    assert b"not supported by Sentinel" in body


def test_profile_enable_disable_flow(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/profile/enable", token=token, method="POST", body={"slug": "fl01", "enabled": False}
    )
    assert status == 200

    status, body, _ = _request(base_url, "/api/v1/profile", token=token)
    data = json.loads(body)
    fl01 = next(f for f in data["favorites"] if f["slug"] == "fl01")
    assert fl01["enabled"] is False


def test_profile_edit_flow(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url,
        "/api/v1/profile/edit",
        token=token,
        method="POST",
        body={"slug": "fl01", "field": "notes", "value": "edited via api"},
    )
    assert status == 200
    status, body, _ = _request(base_url, "/api/v1/catalog/fl01", token=token)
    # baseline entry itself is untouched by profile edits
    assert json.loads(body)["notes"] != "edited via api"

    status, body, _ = _request(base_url, "/api/v1/profile", token=token)
    data = json.loads(body)
    fl01 = next(f for f in data["favorites"] if f["slug"] == "fl01")
    assert fl01["notes"] == "edited via api"


def test_profile_edit_rejects_non_editable_field(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/profile/edit", token=token, method="POST", body={"slug": "fl01", "field": "id", "value": "x"}
    )
    assert status == 400


def test_profile_remove_and_restore_flow(live_server):
    base_url, token, _ = live_server
    _request(base_url, "/api/v1/profile/remove", token=token, method="POST", body={"slug": "fl01"})
    status, body, _ = _request(base_url, "/api/v1/profile", token=token)
    data = json.loads(body)
    assert "fl01" not in {f["slug"] for f in data["favorites"]}

    _request(base_url, "/api/v1/profile/restore", token=token, method="POST", body={"slug": "fl01"})
    status, body, _ = _request(base_url, "/api/v1/profile", token=token)
    data = json.loads(body)
    assert "fl01" in {f["slug"] for f in data["favorites"]}


def test_profile_local_add_and_delete(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url,
        "/api/v1/profile/local",
        token=token,
        method="POST",
        body={"key": "LOCAL01", "favorite_name": "My Local List", "region": "Testland"},
    )
    assert status == 201
    created = json.loads(body)
    assert created["slug"] == "local01"

    status, body, _ = _request(base_url, "/api/v1/profile", token=token)
    data = json.loads(body)
    assert "local01" in {f["slug"] for f in data["favorites"]}

    status, body, _ = _request(base_url, "/api/v1/profile/local/local01", token=token, method="DELETE")
    assert status == 200
    status, body, _ = _request(base_url, "/api/v1/profile", token=token)
    data = json.loads(body)
    assert "local01" not in {f["slug"] for f in data["favorites"]}


def test_preview_endpoint(live_server):
    base_url, token, _ = live_server
    _request(base_url, "/api/v1/profile/enable", token=token, method="POST", body={"slug": "fl01", "enabled": False})
    status, body, _ = _request(base_url, "/api/v1/preview", token=token)
    data = json.loads(body)
    assert len(data["changes"]) == 1
    assert data["changes"][0]["op"] == "disable"


def test_export_endpoints_content_type_and_disposition(live_server):
    base_url, token, _ = live_server
    for fmt, content_type in (("csv", "text/csv"), ("md", "text/markdown"), ("zip", "application/zip")):
        status, body, headers = _request(base_url, f"/api/v1/export/{fmt}", token=token)
        assert status == 200
        assert headers["Content-Type"] == content_type
        assert "attachment" in headers["Content-Disposition"]
        assert len(body) > 0


def test_export_unknown_format(live_server):
    base_url, token, _ = live_server
    status, _, _ = _request(base_url, "/api/v1/export/exe", token=token)
    assert status == 400


def test_generate_endpoint_commits_snapshot(live_server, tmp_path):
    base_url, token, ctx = live_server
    out_dir = tmp_path / "gen-out"
    status, body, _ = _request(
        base_url, "/api/v1/generate", token=token, method="POST", body={"out": str(out_dir), "formats": ["csv"]}
    )
    assert status == 200
    data = json.loads(body)
    assert data["snapshot_id"] == "0001"
    assert (out_dir / "favorites.csv").exists()


def test_generate_endpoint_hpe_format_writes_loose_per_list_files(live_server, tmp_path):
    base_url, token, ctx = live_server
    out_dir = tmp_path / "gen-out"
    status, body, _ = _request(
        base_url, "/api/v1/generate", token=token, method="POST", body={"out": str(out_dir), "formats": ["hpe"]}
    )
    assert status == 200
    data = json.loads(body)
    assert (out_dir / "hpe" / "FL01.hpe").exists()
    assert (out_dir / "hpe" / "FL09a.hpe").exists()
    assert not (out_dir / "hpe" / "FL02.hpe").exists()
    assert any("FL02" in w for w in data["warnings"])


def test_generate_hpe_single_list_download_endpoint(live_server):
    base_url, token, ctx = live_server
    status, body, headers = _request(base_url, "/api/v1/generate/hpe/fl01", token=token)
    assert status == 200
    assert headers["Content-Disposition"] == 'attachment; filename="FL01.hpe"'

    from wasds150.hpe import codec, schema
    from wasds150.hpe.record import parse_records

    text = codec.decode_container(body)
    assert schema.validate_schema(parse_records(text)) == []


def test_generate_hpe_single_list_download_missing_systems_returns_409(live_server):
    base_url, token, ctx = live_server
    # FL02 ("Bravo Dispatch, [E]-ENCRYPTED") has no explicit frequency.
    status, body, _ = _request(base_url, "/api/v1/generate/hpe/fl02", token=token)
    assert status == 409
    assert "FL02" in json.loads(body)["error"]


def test_generate_hpe_single_list_download_unknown_slug_returns_404(live_server):
    base_url, token, ctx = live_server
    status, body, _ = _request(base_url, "/api/v1/generate/hpe/nope", token=token)
    assert status == 404


def test_history_endpoints_and_rollback(live_server, tmp_path):
    base_url, token, ctx = live_server
    out_dir = tmp_path / "gen-out"
    _request(base_url, "/api/v1/generate", token=token, method="POST", body={"out": str(out_dir), "formats": ["csv"]})

    status, body, _ = _request(base_url, "/api/v1/history", token=token)
    data = json.loads(body)
    assert len(data["snapshots"]) == 1
    snap_id = data["snapshots"][0]["id"]

    status, body, _ = _request(base_url, f"/api/v1/history/{snap_id}", token=token)
    assert status == 200

    status, body, _ = _request(base_url, f"/api/v1/history/{snap_id}/rollback", token=token, method="POST", body={})
    assert status == 200



def test_sources_endpoint_lists_static_pack_available(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/sources", token=token)
    data = json.loads(body)
    static_pack = next(s for s in data["sources"] if s["name"] == "static_pack")
    assert static_pack["available"] is True
    placeholder = next(s for s in data["sources"] if s["name"] == "radioreference_free")
    assert placeholder["available"] is False


def test_sources_status_endpoint(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/sources/status", token=token)
    assert status == 200
    data = json.loads(body)
    assert data["offline"] is False
    assert any(s["name"] == "wwara" for s in data["sources"])


def test_sources_configure_endpoint_never_echoes_secrets(live_server):
    base_url, token, ctx = live_server
    status, body, _ = _request(
        base_url,
        "/api/v1/sources/configure",
        token=token,
        method="POST",
        body={"offline": True, "radioreference_username": "alice", "radioreference_app_key": "supersecretkey"},
    )
    assert status == 200
    data = json.loads(body)
    assert data["offline"] is True
    assert data["radioreference_configured"] is True
    assert b"supersecretkey" not in body

    saved = json.loads(ctx.config.sources_config_path.read_text())
    assert saved["radioreference_username"] == "alice"


def test_sources_fetch_endpoint_unconfigured_local_source(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/sources/fetch", token=token, method="POST", body={"name": "sentinel_local"}
    )
    assert status == 400
    data = json.loads(body)
    assert "not configured" in data["error"]


def test_sources_update_endpoint_offline_preview_is_safe_noop(live_server):
    base_url, token, ctx = live_server
    status, body, _ = _request(
        base_url,
        "/api/v1/sources/update",
        token=token,
        method="POST",
        body={"only": ["amsat"], "offline": True, "apply": False},
    )
    assert status == 200
    data = json.loads(body)
    assert data["applied"] is False
    assert data["merge"]["changes"] == []
    assert data["merge"]["conflicts"] == []


def test_sources_provenance_endpoint(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/sources/provenance/fl01", token=token)
    assert status == 200
    data = json.loads(body)
    assert data["slug"] == "fl01"
    assert data["provenance"][0]["source_adapter"] == "static_pack"


def test_sources_provenance_endpoint_unknown_slug(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/sources/provenance/nope", token=token)
    assert status == 404


# ------------------------------------------------------------------- hpe --
def test_hpe_inspect_and_validate_via_content_base64(live_server, synthetic_bcdx36hp_path):
    base_url, token, _ = live_server
    content_base64 = base64.b64encode(synthetic_bcdx36hp_path.read_bytes()).decode("ascii")

    status, body, _ = _request(
        base_url, "/api/v1/hpe/inspect", token=token, method="POST", body={"content_base64": content_base64}
    )
    assert status == 200
    data = json.loads(body)
    assert data["dialect"]["target_model"] == "BCDx36HP"
    assert data["has_signature_line"] is True

    status, body, _ = _request(
        base_url, "/api/v1/hpe/validate", token=token, method="POST", body={"content_base64": content_base64}
    )
    assert status == 200
    data = json.loads(body)
    assert data["issues"] == []


def test_hpe_inspect_via_server_side_path(live_server, synthetic_bcdx36hp_path):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/hpe/inspect", token=token, method="POST", body={"path": str(synthetic_bcdx36hp_path)}
    )
    assert status == 200
    data = json.loads(body)
    assert data["record_count"] > 0


def test_hpe_inspect_requires_content_or_path(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/hpe/inspect", token=token, method="POST", body={})
    assert status == 400


def test_hpe_build_endpoint(live_server):
    base_url, token, _ = live_server
    systems = [
        {
            "id": "s1",
            "label": "Test Conv",
            "departments": [
                {"id": "d1", "label": "Ops", "channels": [{"id": "c1", "label": "Ch1", "freq_mhz": 154.1, "mode": "NFM"}]}
            ],
        }
    ]
    status, body, _ = _request(base_url, "/api/v1/hpe/build", token=token, method="POST", body={"systems": systems})
    assert status == 200
    data = json.loads(body)
    assert data["issues"] == []
    hpe_bytes = base64.b64decode(data["hpe_content_base64"])
    assert hpe_bytes[:1] != b""  # non-empty container bytes


def test_hpe_build_requires_systems(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/hpe/build", token=token, method="POST", body={})
    assert status == 400


# ----------------------------------------------------------------- merge --
def test_merge_preview_and_apply_endpoints(live_server, tmp_path, sample_csv_path):
    import csv

    from wasds150.models.catalog import CSV_FIELDS

    base_url, token, ctx = live_server
    with sample_csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows[0]["favorite_name"] = "Upstream Renamed"
    upstream_path = tmp_path / "upstream.csv"
    with upstream_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_FIELDS), quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)

    status, body, _ = _request(
        base_url, "/api/v1/merge/preview", token=token, method="POST", body={"upstream_path": str(upstream_path)}
    )
    assert status == 200
    data = json.loads(body)
    assert len(data["changes"]) == 1
    assert data["conflicts"] == []

    status, body, _ = _request(
        base_url, "/api/v1/merge/apply", token=token, method="POST", body={"upstream_path": str(upstream_path)}
    )
    assert status == 200
    data = json.loads(body)
    assert data["changes"] == 1
    assert data["conflicts"] == 0

    status, body, _ = _request(base_url, "/api/v1/catalog/fl01", token=token)
    data = json.loads(body)
    assert data["favorite_name"] == "Upstream Renamed"


def test_merge_apply_conflict_requires_force(live_server, tmp_path, sample_csv_path):
    import csv

    from wasds150.models.catalog import CSV_FIELDS

    base_url, token, ctx = live_server
    _request(
        base_url, "/api/v1/profile/edit", token=token, method="POST",
        body={"slug": "fl01", "field": "favorite_name", "value": "My Custom"},
    )

    with sample_csv_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    rows[0]["favorite_name"] = "Upstream Renamed"
    upstream_path = tmp_path / "upstream.csv"
    with upstream_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(CSV_FIELDS), quoting=csv.QUOTE_ALL, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)

    status, body, _ = _request(
        base_url, "/api/v1/merge/apply", token=token, method="POST", body={"upstream_path": str(upstream_path)}
    )
    assert status == 409
    data = json.loads(body)
    assert len(data["conflicts"]) == 1

    status, body, _ = _request(
        base_url, "/api/v1/merge/apply", token=token, method="POST",
        body={"upstream_path": str(upstream_path), "force": True},
    )
    assert status == 200
    data = json.loads(body)
    assert data["conflicts"] == 1


def test_merge_preview_requires_upstream_path(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/merge/preview", token=token, method="POST", body={})
    assert status == 400


# --------------------------------------------------------------- install --
def test_install_detect_endpoint(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP").mkdir(parents=True)
    query = urllib.parse.urlencode({"dir": str(card)})
    status, body, _ = _request(base_url, f"/api/v1/install/detect?{query}", token=token)
    assert status == 200
    data = json.loads(body)
    assert len(data["volumes"]) == 1
    assert data["volumes"][0]["is_sds150_candidate"] is True


def test_preview_reports_invalid_profile_as_422(live_server):
    base_url, token, ctx = live_server
    profile = ctx.load_profile()
    profile.set_enabled("unknown-baseline-slug", True)
    ctx.save_profile(profile)

    status, body, _ = _request(base_url, "/api/v1/preview", token=token)
    assert status == 422
    assert "unknown baseline slug" in json.loads(body)["error"]


def test_install_backup_endpoint(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    (card / "BCDx36HP" / "profile.cfg").write_text("x", encoding="ascii")

    status, body, _ = _request(
        base_url, "/api/v1/install/backup", token=token, method="POST",
        body={"mount": str(card), "out_dir": str(tmp_path / "backups")},
    )
    assert status == 200
    data = json.loads(body)
    assert data["verify_issues"] == []


def test_install_write_dry_run_and_execute_endpoints(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    (card / "BCDx36HP" / "app_data.cfg").write_text("resume", encoding="ascii")
    systems = [
        {
            "id": "s1",
            "label": "Test",
            "departments": [
                {
                    "id": "d1",
                    "label": "Ops",
                    "channels": [{"id": "c1", "label": "Test", "freq_mhz": 154.1, "mode": "NFM"}],
                }
            ],
        }
    ]

    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={
            "mount": str(card), "systems": systems, "index": 0, "user_name": "Test List",
            "backup_dir": str(tmp_path / "backups"),
        },
    )
    assert status == 200
    data = json.loads(body)
    assert data["dry_run"] is True

    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={
            "mount": str(card), "systems": systems, "index": 0, "user_name": "Test List",
            "backup_dir": str(tmp_path / "backups"), "execute": True, "confirm": f"WRITE {card.name}",
        },
    )
    assert status == 200
    data = json.loads(body)
    assert data["verified"] is True
    assert data["backup_path"] is not None


def test_install_write_execute_wrong_confirm_rejected(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={
            "mount": str(card), "systems": [], "index": 0, "user_name": "Test",
            "backup_dir": str(tmp_path / "backups"), "execute": True, "confirm": "wrong",
        },
    )
    assert status == 400


def test_install_write_by_slug_default_workflow(live_server, tmp_path):
    """The default install workflow via the web UI: profile -> generated
    favorites -> install, with no Systems JSON in the request body at
    all. FL01's "ALPHA1 155.000" carries an explicit literal frequency."""
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)

    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={"mount": str(card), "slug": "fl01", "index": 0, "backup_dir": str(tmp_path / "backups")},
    )
    assert status == 200
    data = json.loads(body)
    assert data["dry_run"] is True
    assert "BCDx36HP/favorites_lists/f_000000.hpd" in data["planned_writes"]


def test_install_write_by_slug_with_no_systems_returns_409(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)

    # FL02 ("Bravo Dispatch, [E]-ENCRYPTED") has no explicit frequency.
    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={"mount": str(card), "slug": "fl02", "index": 0, "backup_dir": str(tmp_path / "backups")},
    )
    assert status == 409
    assert "FL02" in json.loads(body)["error"]


def test_install_write_unknown_slug_returns_404(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={"mount": str(card), "slug": "nope", "index": 0, "backup_dir": str(tmp_path / "backups")},
    )
    assert status == 404


def test_install_write_requires_exactly_one_of_slug_or_systems(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)

    # Neither given.
    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={"mount": str(card), "index": 0, "backup_dir": str(tmp_path / "backups")},
    )
    assert status == 400
    assert "exactly one" in json.loads(body)["error"]

    # Both given.
    status, body, _ = _request(
        base_url, "/api/v1/install/write", token=token, method="POST",
        body={
            "mount": str(card), "slug": "fl01", "systems": [], "index": 0,
            "backup_dir": str(tmp_path / "backups"),
        },
    )
    assert status == 400
    assert "exactly one" in json.loads(body)["error"]


def test_install_rollback_endpoint(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    (card / "BCDx36HP" / "app_data.cfg").write_text("resume", encoding="ascii")

    status, body, _ = _request(
        base_url, "/api/v1/install/backup", token=token, method="POST",
        body={"mount": str(card), "out_dir": str(tmp_path / "backups")},
    )
    backup_path = json.loads(body)["backup_path"]

    (card / "BCDx36HP" / "app_data.cfg").unlink()

    status, body, _ = _request(
        base_url, "/api/v1/install/rollback", token=token, method="POST",
        body={"mount": str(card), "backup": backup_path},
    )
    assert status == 200
    data = json.loads(body)
    assert "BCDx36HP/app_data.cfg" in data["restored"]


# ------------------------------------------------------------------ hpdb --
def test_hpdb_inspect_cfg_and_state_endpoints(live_server, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    base_url, token, _ = live_server

    status, body, _ = _request(
        base_url, "/api/v1/hpdb/inspect", token=token, method="POST",
        body={"path": str(synthetic_hpdb_cfg_path)},
    )
    assert status == 200
    data = json.loads(body)
    assert data["kind"] == "hpdb_index"
    assert data["states"]["53"] == "Washington"

    status, body, _ = _request(
        base_url, "/api/v1/hpdb/inspect", token=token, method="POST",
        body={"path": str(synthetic_hpdb_state_path)},
    )
    assert status == 200
    data = json.loads(body)
    assert data["kind"] == "hpdb_state"
    names = {s["name"] for s in data["systems"]}
    assert names == {"King County Public Safety", "Regional P25"}


def test_hpdb_inspect_via_content_base64(live_server, synthetic_hpdb_state_path):
    base_url, token, _ = live_server
    content_base64 = base64.b64encode(synthetic_hpdb_state_path.read_bytes()).decode("ascii")
    status, body, _ = _request(
        base_url, "/api/v1/hpdb/inspect", token=token, method="POST", body={"content_base64": content_base64}
    )
    assert status == 200
    data = json.loads(body)
    assert len(data["systems"]) == 2


def test_hpdb_inspect_requires_content_or_path(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/hpdb/inspect", token=token, method="POST", body={})
    assert status == 400


def test_hpdb_extract_by_county_endpoint(live_server, synthetic_hpdb_state_path):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/hpdb/extract", token=token, method="POST",
        body={"path": str(synthetic_hpdb_state_path), "county_id": 5302},
    )
    assert status == 200
    data = json.loads(body)
    assert data["matched_systems"] == ["Regional P25"]
    hpe_bytes = base64.b64decode(data["hpe_content_base64"])
    assert len(hpe_bytes) > 0


def test_hpdb_extract_by_radius_endpoint(live_server, synthetic_hpdb_state_path):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/hpdb/extract", token=token, method="POST",
        body={"path": str(synthetic_hpdb_state_path), "within": {"lat": 47.6, "lon": -122.33, "radius_mi": 1}},
    )
    assert status == 200
    data = json.loads(body)
    assert set(data["matched_systems"]) == {"King County Public Safety", "Regional P25"}


def test_hpdb_extract_no_match_returns_404(live_server, synthetic_hpdb_state_path):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/hpdb/extract", token=token, method="POST",
        body={"path": str(synthetic_hpdb_state_path), "county_id": 99999},
    )
    assert status == 404


def test_hpdb_extract_rejects_cfg_input(live_server, synthetic_hpdb_cfg_path):
    base_url, token, _ = live_server
    status, body, _ = _request(
        base_url, "/api/v1/hpdb/extract", token=token, method="POST",
        body={"path": str(synthetic_hpdb_cfg_path), "county_id": 1},
    )
    assert status == 400


def test_install_hpdb_inspect_endpoint(live_server, tmp_path, synthetic_hpdb_cfg_path, synthetic_hpdb_state_path):
    import shutil

    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "HPDB").mkdir(parents=True)
    shutil.copy(synthetic_hpdb_cfg_path, card / "BCDx36HP" / "HPDB" / "hpdb.cfg")
    shutil.copy(synthetic_hpdb_state_path, card / "BCDx36HP" / "HPDB" / "s_000053.hpd")

    query = urllib.parse.urlencode({"mount": str(card)})
    status, body, _ = _request(base_url, f"/api/v1/install/hpdb-inspect?{query}", token=token)
    assert status == 200
    data = json.loads(body)
    assert data["states"]["53"] == "Washington"
    assert set(data["state_files"]["53"]) == {"King County Public Safety", "Regional P25"}


def test_install_hpdb_inspect_missing_hpdb_returns_404(live_server, tmp_path):
    base_url, token, _ = live_server
    card = tmp_path / "card"
    (card / "BCDx36HP" / "favorites_lists").mkdir(parents=True)
    query = urllib.parse.urlencode({"mount": str(card)})
    status, body, _ = _request(base_url, f"/api/v1/install/hpdb-inspect?{query}", token=token)
    assert status == 404


def test_install_hpdb_inspect_requires_mount(live_server):
    base_url, token, _ = live_server
    status, body, _ = _request(base_url, "/api/v1/install/hpdb-inspect", token=token)
    assert status == 400
