"""The amateur repeater registry merges every source's copy of a machine into
one record: coordination decides identity, each field comes from the best
source. Invented calls throughout."""
from wasds150.catalog.puget_ham import WWARA_SYSTEM_ID
from wasds150.catalog.repeater_registry import DSTARFM_KEY, DSTARINFO_KEY, build_registry
from wasds150.models.catalog import CSV_FIELDS, Catalog, Channel, Department, FavoritesList, System
from wasds150.util.hashing import stable_id

HOME = (47.6351, -121.9954)
RB = "state: Washington; RepeaterBook data via DSTARInfo (personal use only)"


def _fl(key, *systems):
    row = {name: "" for name in CSV_FIELDS}
    row.update(favorite_key=key, favorite_name=f"{key} list")
    favorite = FavoritesList.from_csv_row(row)
    favorite.systems = list(systems)
    return favorite


def _system(system_id, department, *channels):
    return System(id=system_id, label=system_id, departments=[Department(id=f"{system_id}:{department}", label=department, channels=list(channels))])


def _registry(*favorites):
    registry = build_registry(Catalog(favorites=list(favorites)), home=HOME)
    return {c.label: (d.label, c) for s in registry.systems for d in s.departments for c in d.channels}


def _fm(label, freq, tx, *, tone="", lat=None, lon=None, notes="", mode="FM"):
    return Channel(id=f"{label}:{freq}:{lat}", label=label, freq_mhz=freq, tx_freq_mhz=tx, mode=mode, tone=tone, tx_tone=tone,
                   lat=lat, lon=lon, notes=notes)


def test_coordination_decides_which_copies_are_one_machine():
    wwara = _system(
        WWARA_SYSTEM_ID, "Seattle Metro - Analog",
        _fm("W7ABC - Redmond", 147.0, 146.4, tone="TONE=C103.5", lat=47.67, lon=-122.12, notes="input 146.4; W7ABC"),
        _fm("KJ7JNK - Redmond", 440.675, 445.675, tone="TONE=C103.5", lat=47.69, lon=-122.11),
        _fm("NM7R - Naselle", 440.675, 445.675, tone="TONE=C118.8", lat=46.42, lon=-123.80),
        _fm("W7AAA - Rattlesnake", 145.11, 144.51, tone="TONE=C103.5", lat=47.46, lon=-121.80),
        _fm("W7AAA - Skykomish", 145.11, 144.51, tone="TONE=C123", lat=47.71, lon=-121.36),
        _fm("W7PFB - Carnation", 223.9, 222.3, tone="TONE=C88.5", lat=47.68, lon=-121.89),
        _fm("W7BU - Meglar Mtn", 440.925, 445.925, tone="TONE=C118.8", lat=46.26, lon=-123.89),
    )
    records = _registry(
        _fl("PSHAM01", wwara),
        _fl("FL60", _system(stable_id("fl60:coordination", kind="system"), "Coordinated Repeaters",
                            _fm("N7KGS (Ellensburg, Kittitas Co.)", 146.72, 146.12, tone="TONE=C131.8"))),
        _fl("RRC-KING", _system("rr", "King County Amateur Radio",
                                Channel(id="rr1", label="KBARA Hub Repeater", freq_mhz=223.9, tx_freq_mhz=222.3, mode="FM",
                                        notes="callsign: AK2O"),
                                Channel(id="rr2", label="Club Hub", freq_mhz=440.675, tx_freq_mhz=445.675, mode="FM"))),
        _fl(DSTARFM_KEY, _system("fm", "Washington",
                                 _fm("W7ABC - Redmond", 147.0, 146.4, tone="TONE=C100", lat=47.70, lon=-122.10, notes=RB),
                                 _fm("N6OBY - Redmond", 440.675, 445.675, tone="TONE=C103.5", lat=47.60, lon=-122.11, notes=RB),
                                 _fm("W7AAA - North Bend", 145.11, 144.51, tone="TONE=C127.3", lat=47.46, lon=-121.80, notes=RB),
                                 _fm("W7BU - Chinook", 440.925, 435.925, tone="TONE=C118.8", lat=46.27, lon=-123.88, notes=RB),
                                 _fm("N7KGS - Ellensburg", 146.72, 146.12, tone="TONE=C131.8", lat=46.99, lon=-120.55, notes=RB),
                                 _fm("W7ABC - Spokane", 147.0, 146.4, tone="TONE=C100", lat=47.66, lon=-117.43, notes=RB),
                                 _fm("KE7NEW - Carnation", 145.59, 144.99, tone="TONE=C162.2", lat=47.64, lon=-121.91, notes=RB),
                                 _fm("W7ORE - Portland", 147.0, 147.6, tone="TONE=C107.2", lat=45.52, lon=-122.68,
                                     notes="state: Oregon; RepeaterBook"),
                                 _fm("W6FAR - Los Angeles", 147.0, 147.6, lat=34.05, lon=-118.24, notes="state: California"))),
    )
    assert sorted(records) == sorted([
        "W7ABC - Redmond", "KJ7JNK - Redmond", "NM7R - Naselle", "W7AAA - Rattlesnake", "W7AAA - Skykomish",
        "W7PFB - Carnation", "W7BU - Meglar Mtn", "N7KGS - Ellensburg", "W7ABC - Spokane", "KE7NEW - Carnation",
        "W7ORE - Portland",
    ])
    # WWARA's position, tone and name win over the RepeaterBook copy of the same call.
    department, w7abc = records["W7ABC - Redmond"]
    assert department == "Washington - Analog 2 Meter"
    assert (w7abc.lat, w7abc.tx_tone) == (47.67, "TONE=C103.5") and "position: WWARA" in w7abc.notes
    # An owner's call on a coordinated pair nearby is that machine (N6OBY on KJ7JNK's pair).
    assert "RepeaterBook via DSTARInfo" in records["KJ7JNK - Redmond"][1].notes
    # Two coordinated machines sharing a call and output stay two; the copy joins the nearer, keeping WWARA's tone.
    assert records["W7AAA - Rattlesnake"][1].tx_tone == "TONE=C103.5" and "RepeaterBook" in records["W7AAA - Rattlesnake"][1].notes
    # A county description on the one coordinated pair joins it; one that fits two machines is left out.
    assert "RadioReference" in records["W7PFB - Carnation"][1].notes
    assert "Club Hub" not in records
    # RepeaterBook's wrong input loses to WWARA's; IACC's record takes RepeaterBook's position.
    assert records["W7BU - Meglar Mtn"][1].tx_freq_mhz == 445.925
    _dept, kgs = records["N7KGS - Ellensburg"]
    assert (kgs.lat, kgs.tx_freq_mhz) == (46.99, 146.12) and "(approximate)" in kgs.notes
    # An uncoordinated repeater stands alone; other states have their own departments; far ones are left out.
    assert records["KE7NEW - Carnation"][0] == "Washington - Analog 2 Meter"
    assert records["W7ORE - Portland"][0] == "Oregon - Analog 2 Meter"


def test_mixed_and_digital_coordination_anchors_its_pair():
    def digital(label, freq, tx, mode, tone, access, notes, lat, lon):
        return Channel(id=label, label=label, freq_mhz=freq, tx_freq_mhz=tx, mode=mode, tone=tone, tx_tone=access,
                       lat=lat, lon=lon, notes=notes)

    wwara = _system(
        WWARA_SYSTEM_ID, "Eastside & Cascades - P25 Digital",
        digital("W7MIX - Tiger Mtn", 444.85, 449.85, "P25", "NAC=293", "TONE=C103.5", "input 449.85; FM/P25; club",
                47.54, -122.11),
        digital("W7DIG - Gold Mtn", 442.65, 447.65, "DMR", "ColorCode=1", "TONE=C103.5", "input 447.65; DMR",
                47.55, -122.81),
    )
    records = _registry(
        _fl("PSHAM01", wwara),
        _fl("FL60", _system(stable_id("fl60:coordination", kind="system"), "Coordinated Repeaters",
                            _fm("K7EST (Moses Lake, Grant Co.)", 146.425, 147.425, tone="TONE=C100"))),
        _fl(DSTARFM_KEY, _system("fm", "Washington",
                                 _fm("KB7OWN - Bellevue", 444.85, 449.85, tone="TONE=C103.5", lat=47.56, lon=-122.11, notes=RB),
                                 _fm("WB7TRS - Bremerton", 442.65, 447.65, tone="TONE=C103.5", lat=47.55, lon=-122.78, notes=RB),
                                 _fm("VE7FAR - Barriere", 146.425, 147.425, lat=52.14, lon=-120.13,
                                     notes="state: British Columbia"))),
    )
    # A mixed machine is programmed analog, named and toned by WWARA, whatever call RepeaterBook used.
    department, mixed = records["W7MIX - Tiger Mtn"]
    assert (department, mixed.mode, mixed.tone, mixed.tx_tone) == ("Washington - Analog 70 Centimeter", "FM", "TONE=C103.5", "TONE=C103.5")
    assert "RepeaterBook" in mixed.notes and "KB7OWN - Bellevue" not in records
    # A DMR-only machine keeps its pair: RepeaterBook's analog listing of it is not a second machine.
    assert "W7DIG - Gold Mtn" not in records and "WB7TRS - Bremerton" not in records
    # IACC publishes no position: a listing elsewhere under another call is its own machine.
    iacc = records["K7EST - Moses Lake"][1]
    assert iacc.lat is None and "VE7FAR - Barriere" in records


def test_a_dstar_module_merges_by_call_and_keeps_wwaras_pair():
    wwara = _system(
        WWARA_SYSTEM_ID, "Seattle Metro - Unsupported Digital - D-Star",
        _fm("K7XYZ - Bellevue", 146.4125, 147.4125, mode="AUTO", lat=47.6165, lon=-122.2017, notes="input 147.4125; D-Star"),
        _fm("W7QRS - Issaquah", 147.995, 147.395, mode="AUTO", lat=47.54, lon=-122.10, notes="input 147.395; D-Star; coordination expired"),
    )
    wwara.departments[0].channels[0].avoid = True  # the scanner cannot decode it; a radio can
    directory = _system("ds", "Washington",
                        Channel(id="d1", label="K7XYZ C - Bellevue", freq_mhz=146.4125, tx_freq_mhz=147.4125, mode="DV",
                                dv_rpt1="K7XYZ  C", dv_rpt2="K7XYZ  G", lat=47.62, lon=-122.20, notes="state: Washington"),
                        Channel(id="d2", label="W7QRS C - Newcastle", freq_mhz=147.95, tx_freq_mhz=146.95, mode="DV",
                                dv_rpt1="W7QRS  C", dv_rpt2="W7QRS  G", lat=47.54, lon=-122.10, notes="state: Washington"))
    records = _registry(_fl("PSHAM01", wwara), _fl(DSTARINFO_KEY, directory))
    department, k7xyz = records["K7XYZ C - Bellevue"]
    assert department == "Washington - D-STAR"
    assert (k7xyz.mode, k7xyz.dv_rpt1, k7xyz.dv_rpt2, k7xyz.avoid) == ("DV", "K7XYZ  C", "K7XYZ  G", False)
    _dept, w7qrs = records["W7QRS C - Issaquah"]
    # DSTARInfo's stale pair loses to WWARA's; WWARA's lapsed coordination is kept out of radios.
    assert (w7qrs.freq_mhz, w7qrs.tx_freq_mhz, w7qrs.avoid) == (147.995, 147.395, True)
    assert len(records) == 2
