# Ames Lake, King County, and Outdoor Favorites Lists

This extension adds local operational profiles centered on Ames Lake and ZIP
98053, one Favorites List for every incorporated city or town wholly or partly
in King County, a broader Eastside profile, and a comprehensive outdoor safety
rollup.

No licensed frequencies, sites, TGIDs, or HPDB records are checked into the
repository. Public rows define intent and location only. Actual systems are
matched by exact Sentinel/RadioReference system identity and populated from the
user's updated local Sentinel database.

## Generated local lists

| Key | Place/profile | Census center | Radius |
|---|---|---:|---:|
| KC01 | Algona | 47.281987, -122.250467 | 6 mi |
| KC02 | Auburn | 47.303773, -122.210000 | 12 mi |
| KC03 | Beaux Arts Village | 47.585343, -122.203646 | 5 mi |
| KC04 | Bellevue | 47.597837, -122.156480 | 10 mi |
| KC05 | Black Diamond | 47.314748, -122.017685 | 8 mi |
| KC06 | Bothell | 47.773531, -122.204376 | 10 mi |
| KC07 | Burien | 47.475605, -122.344661 | 10 mi |
| KC08 | Carnation | 47.644188, -121.900670 | 7 mi |
| KC09 | Clyde Hill | 47.630354, -122.217983 | 5 mi |
| KC10 | Covington | 47.364793, -122.104561 | 9 mi |
| KC11 | Des Moines | 47.388708, -122.317581 | 9 mi |
| KC12 | Duvall | 47.735512, -121.972224 | 7 mi |
| KC13 | Enumclaw | 47.202179, -121.988976 | 9 mi |
| KC14 | Federal Way | 47.311596, -122.337757 | 12 mi |
| KC15 | Hunts Point | 47.642958, -122.229197 | 5 mi |
| KC16 | Issaquah | 47.544488, -122.049085 | 9 mi |
| KC17 | Kenmore | 47.749858, -122.247244 | 7 mi |
| KC18 | Kent | 47.387970, -122.212727 | 12 mi |
| KC19 | Kirkland | 47.696658, -122.204170 | 9 mi |
| KC20 | Lake Forest Park | 47.758911, -122.291729 | 6 mi |
| KC21 | Maple Valley | 47.367147, -122.034815 | 9 mi |
| KC22 | Medina | 47.626541, -122.242866 | 5 mi |
| KC23 | Mercer Island | 47.564004, -122.231214 | 7 mi |
| KC24 | Milton | 47.251994, -122.317289 | 7 mi |
| KC25 | Newcastle | 47.531486, -122.165582 | 7 mi |
| KC26 | Normandy Park | 47.432975, -122.344689 | 6 mi |
| KC27 | North Bend | 47.487967, -121.768786 | 9 mi |
| KC28 | Pacific | 47.261974, -122.252429 | 6 mi |
| KC29 | Redmond | 47.677924, -122.115336 | 10 mi |
| KC30 | Renton | 47.479190, -122.194613 | 12 mi |
| KC31 | Sammamish | 47.594268, -122.038081 | 10 mi |
| KC32 | SeaTac | 47.443403, -122.298287 | 10 mi |
| KC33 | Seattle | 47.619335, -122.351538 | 15 mi |
| KC34 | Shoreline | 47.756917, -122.345505 | 10 mi |
| KC35 | Skykomish | 47.709852, -121.356448 | 8 mi |
| KC36 | Snoqualmie | 47.543245, -121.868645 | 9 mi |
| KC37 | Tukwila | 47.476289, -122.275740 | 9 mi |
| KC38 | Woodinville | 47.757695, -122.146791 | 8 mi |
| KC39 | Yarrow Point | 47.644576, -122.219994 | 5 mi |
| LA01 | Ames Lake Home Area | 47.633966, -121.960584 | 22 mi |
| LA17 | Eastside King Regional | 47.633966, -121.960584 | 35 mi |

Every retained department receives the list's center, radius, and `Circle`
shape. Sentinel site coordinates remain intact. The department location tags
make each list useful with GPS/location control even though regional trunked
sites serve multiple municipalities.

## Included service categories

Each city list is independently curated from exact matched systems. Depending
on the municipality and dispatch provider, it can contain:

- city public works, streets, water, transportation, and citywide operations;
- NORCOM or Valley Communications fire dispatch, fire tactical, EMS, ambulance,
  and operations;
- King County emergency management, incident management, PSAP common, mutual
  aid, and interoperability;
- nearby hospital common and EMS coordination;
- reviewed transit operations for the regional profile; and
- police/sheriff reference groups retained as `[E]-ENCRYPTED`, set to Avoid.

Unmatched departments and channels are omitted. No encryption state, dispatch
assignment, frequency, TGID, site, tone, or mode is invented. Milton includes
the exact locally matched PSERN and PSRS systems needed to retain the reviewed
Sumner/Milton shared police reference.

## Outdoor safety rollup

`OUT01 — WA Outdoor Safety - All` deep-copies only populated, validated
component lists and currently combines 38 distinct systems:

- statewide SAR, mutual aid, NPSPAC/STATEOPS, CEMNET, WSP, WSDOT, DNR, and
  NIFC;
- clear King County fire/EMS/transit operations;
- every Washington mountain, national park/forest, Cascades, Gorge, and
  highlands profile;
- civil aviation, Seattle Center/FSS, rescue, and medevac aviation;
- USCG/marine, ferries/VTS, ports, and commercial marine;
- amateur repeaters, linked systems, ARES/RACES/ACS, and simplex/calling;
- GMRS/FRS/NWAC, MURS, and CB;
- hospital/medevac, tow/road, and NOAA Weather components.

Discovery-only ski and venue lists and encrypted law lists are excluded. The
rollup preserves component location metadata and derived provenance. Because it
is intentionally large, use location control and disable distant systems for a
practical scan cycle.

## Refresh workflow

After updating Sentinel's master database:

1. Run a `sentinel_local` source preview.
2. Confirm every `KC*`, `LA*`, and `OUT01` row reports full coverage.
3. Apply without `--force` after reviewing conflicts.
4. Generate the import pack and validate every HPE.
5. Inspect representative city lists, location tags, clear/encrypted grouping,
   and `OUT01` in Sentinel before writing to the scanner.

The current local validation produced 136 catalog entries and 134 HPE files;
only FL45 and FL72 remain intentional Discovery-only gaps.

## Sources

- U.S. Census Bureau, 2023 Gazetteer, Washington places (official internal
  points used for the 39 municipal location tags):
  https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2023_Gazetteer/2023_gaz_place_53.txt
- King County municipal and sheriff service information:
  https://kingcounty.gov/
- NORCOM consolidated dispatch:
  https://www.norcom.org/
- Eastside Fire & Rescue service information:
  https://www.eastsidefire-rescue.org/
- Valley Communications Center:
  https://www.valleycom.org/
- RadioReference PSERN system identity (user-local Sentinel data supplies the
  licensed records): https://www.radioreference.com/db/sid/11628
- Washington DNR wildfire resources:
  https://www.dnr.wa.gov/WildfireResources

Public sources establish place centers, agency relationships, and list intent.
The local Sentinel database remains the authority for the actual radio record
hierarchy.
