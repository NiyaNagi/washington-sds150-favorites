"""Lake Ozette and the north-west Olympic coast.

Structured, individually cited channels for the corner of Washington that the
statewide catalog covers only thinly: Clallam County west of the Elwha, the
Makah and Quileute reservations, Olympic National Park's coastal strip, and
the shipping lanes off Cape Alava.

Unlike most catalog rows, these channels are built as structured
:class:`~wasds150.models.catalog.Channel` objects rather than parsed out of
free text.  That is deliberate: a transceiver needs the repeater input and the
access tone as separate values, and a prose channel list cannot carry them
without guessing.

Sourcing rules applied throughout:

* Every frequency below appears in a cited public record.  Where a record
  publishes no tone - FCC ULS never carries CTCSS, for instance - the tone is
  left empty rather than filled in from a plausible neighbour.
* Repeater inputs come from the licence record or the coordination database.
  None are derived from band-plan convention.
* Frequencies the radio cannot use, or that carry digital traffic an analog
  radio cannot decode, are simply absent. They are documented in
  ``docs/ozette-lake.md`` so the omission is auditable.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.util.hashing import stable_id

#: USGS GNIS "Ozette Lake", feature ID 1531490, Clallam County.
OZETTE_LAT = 48.0947448
OZETTE_LON = -124.6372175
#: USGS GNIS "Cape Alava", feature ID 1503792 - the coastal end of the trail.
CAPE_ALAVA_LAT = 48.1658959
CAPE_ALAVA_LON = -124.7324598

GNIS_SOURCE = "https://prd-tnm.s3.amazonaws.com/StagedProducts/GeographicNames/DomesticNames/DomesticNames_WA_Text.zip"
NPS_OZETTE_URL = "https://www.nps.gov/olym/planyourvisit/visiting-ozette.htm"

#: Radius used for scanner location control on departments in this list.
OZETTE_RANGE_MILES = 60.0

# Sentinel service-type codes, from wasds150.hpe.schema.SERVICE_TYPES.
_ST_LAW = 1
_ST_FIRE = 2
_ST_EMS = 12
_ST_HAM = 13
_ST_AVIATION = 15
_ST_MARINE = 16
_ST_BUSINESS = 17
_ST_TRANSPORT = 26
_ST_MILITARY = 30
_ST_UTILITIES = 34
_ST_OTHER = 21

# ---------------------------------------------------------------------------
# Channel tables.
#
# (label, rx_mhz, tone, mode, service_type, tx_mhz, tx_tone, note)
# ---------------------------------------------------------------------------

ChannelRow = Tuple[str, float, str, str, int, Optional[float], str, str]

_RR_FED = "https://www.radioreference.com/db/aid/2373"
_RR_DNR = "https://www.radioreference.com/db/aid/2372"
_RR_CLALLAM = "https://www.radioreference.com/db/browse/ctid/2962"
_RR_MUTUAL_AID = "https://www.radioreference.com/db/aid/2371"
_RR_NAT_INTEROP = "https://www.radioreference.com/db/aid/7742"
_RR_ZSE = "https://www.radioreference.com/db/aid/2235"
_RR_MARINE = "https://www.radioreference.com/db/aid/7748"
_NAVCEN_VTS = "https://www.navcen.uscg.gov/vessel-traffic-services-radio-procedures"
_NWS_STATIONS = "https://www.weather.gov/nwr/stations?State=WA"
_WAFOG = "https://mil.wa.gov/asset/6a1eeab054e7c/Washington-Field-Operations-Guide_FOG_1.10.pdf"
_ULS = "https://data.fcc.gov/download/pub/uls/complete/l_LMpriv.zip"
_REPEATERBOOK_CLALLAM = "https://www.repeaterbook.com/repeaters/location_search.php?type=county&loc=Clallam&state_id=53"

NPS_USFS: Sequence[ChannelRow] = (
    ("Olympic NP Primary", 168.525, "", "NFM", _ST_OTHER, None, "", f"NPS Olympic National Park primary repeater, carrier squelch; {_RR_FED}"),
    ("Olympic NP Air-Ground", 166.9625, "TONE=C100", "NFM", _ST_OTHER, None, "", f"NPS Olympic NP air-to-ground; {_RR_FED}"),
    ("ONF Pacific Ranger Dist", 171.550, "TONE=C123", "NFM", _ST_OTHER, None, "", f"Olympic National Forest Pacific Ranger District repeater; {_RR_FED}"),
    ("ONF Hood Canal Ranger Dist", 171.475, "TONE=C123", "NFM", _ST_OTHER, None, "", f"Olympic National Forest Hood Canal Ranger District repeater; {_RR_FED}"),
    ("USFS Air Guard", 168.625, "", "NFM", _ST_AVIATION, None, "", f"National USFS air guard; {_RR_FED}"),
    ("USFS Air-Ground H R6", 167.475, "", "NFM", _ST_AVIATION, None, "", f"USFS air-to-ground H, Region 6 common; {_RR_FED}"),
    ("USFS Incident Command", 168.550, "", "NFM", _ST_FIRE, None, "", f"USFS incident command post; {_RR_FED}"),
    ("USFS Law Enforcement", 168.025, "", "NFM", _ST_LAW, None, "", f"USFS law enforcement common; {_RR_FED}"),
    ("DOI Air-Ground Kilo", 167.075, "", "NFM", _ST_AVIATION, None, "", f"Department of the Interior air-to-ground Kilo; {_RR_FED}"),
)

DNR: Sequence[ChannelRow] = (
    ("DNR Ozette", 159.255, "TONE=C192.8", "NFM", _ST_FIRE, None, "", f"WA DNR Olympic Region Ozette repeater, call KCU803; {_RR_DNR}"),
    ("DNR Straits", 159.300, "TONE=C173.8", "NFM", _ST_FIRE, None, "", f"WA DNR Olympic Region Straits repeater, call WNFD816; {_RR_DNR}"),
    ("DNR Hoh", 159.2025, "D365", "NFM", _ST_FIRE, None, "", f"WA DNR Olympic Region Hoh repeater, call KJY894; {_RR_DNR}"),
    ("DNR Quinault", 159.4575, "TONE=C127.3", "NFM", _ST_FIRE, None, "", f"WA DNR Olympic Region Quinault repeater, call KBB856; {_RR_DNR}"),
    ("DNR Canal", 159.345, "TONE=C103.5", "NFM", _ST_FIRE, None, "", f"WA DNR Olympic Region Canal repeater; {_RR_DNR}"),
    ("DNR State Net", 159.420, "", "NFM", _ST_FIRE, None, "", f"WA DNR statewide net, call KE9669; {_RR_DNR}"),
    ("DNR Common", 151.415, "TONE=C103.5", "NFM", _ST_FIRE, None, "", f"WA DNR statewide common; {_RR_DNR}"),
    ("DNR Tac 1", 151.310, "TONE=C103.5", "NFM", _ST_FIRE, None, "", f"WA DNR tactical 1; {_RR_DNR}"),
    ("DNR Tac 2", 151.340, "TONE=C103.5", "NFM", _ST_FIRE, None, "", f"WA DNR tactical 2; {_RR_DNR}"),
    ("DNR Flight Following", 151.3475, "", "NFM", _ST_AVIATION, None, "", f"WA DNR aircraft flight following; {_RR_DNR}"),
    ("DNR Air-Ground 1", 159.270, "TONE=C103.5", "NFM", _ST_AVIATION, None, "", f"WA DNR air-to-ground 1, call KQP444; {_RR_DNR}"),
)

CLALLAM: Sequence[ChannelRow] = (
    ("Clallam West Dispatch", 453.375, "TONE=C103.5", "NFM", _ST_LAW, None, "", f"Clallam County west dispatch: Sheriff, Forks PD, La Push PD, call WQGU670; {_RR_CLALLAM}"),
    ("Clallam East Tac", 453.275, "TONE=C103.5", "NFM", _ST_LAW, None, "", f"Clallam County east tactical, call KVN623; {_RR_CLALLAM}"),
    ("Clallam Fire Dispatch", 155.820, "TONE=C100", "NFM", _ST_FIRE, None, "", f"Clallam County Fire District 2 dispatch, call WQME701; {_RR_CLALLAM}"),
    ("Joyce Fire Dispatch", 155.7225, "TONE=C100", "NFM", _ST_FIRE, None, "", f"Clallam County Fire District 4 Joyce dispatch, call WQLB410; {_RR_CLALLAM}"),
    ("Joyce Fire Tac", 154.445, "", "NFM", _ST_FIRE, None, "", f"Clallam County Fire District 4 Joyce; {_RR_CLALLAM}"),
    ("Sequim Fire Dispatch", 155.7825, "TONE=C123", "NFM", _ST_FIRE, None, "", f"Sequim fire dispatch, call WQCH837; {_RR_CLALLAM}"),
    ("Port Angeles Police", 460.100, "TONE=C103.5", "NFM", _ST_LAW, None, "", f"Port Angeles Police dispatch, call KNBW381; {_RR_CLALLAM}"),
    ("Clallam Public Works A", 155.925, "TONE=C118.8", "NFM", _ST_UTILITIES, None, "", f"Clallam County public works A, call KPN31; {_RR_CLALLAM}"),
    ("Clallam Public Works B", 158.835, "TONE=C118.8", "NFM", _ST_UTILITIES, None, "", f"Clallam County public works B, call KPN31; {_RR_CLALLAM}"),
    ("Forks City", 453.975, "", "NFM", _ST_UTILITIES, 458.975, "", f"City of Forks repeater, call WPFC946, input 458.975; tone not published in ULS; {_ULS}"),
)

TRIBAL: Sequence[ChannelRow] = (
    ("Makah Tribal Police", 155.070, "", "NFM", _ST_LAW, 159.210, "", f"Makah Indian Nation Tribal Police, call KKC738, Bahokus Peak, input 159.210; tone not published in ULS; {_ULS}"),
    ("Makah Tribal Council", 453.700, "", "NFM", _ST_UTILITIES, 458.700, "", f"Makah Tribal Council, call WSNH246, Bahokus Peak, input 458.700; tone not published in ULS; {_ULS}"),
    ("Quileute Fire", 460.2125, "", "NFM", _ST_FIRE, 465.2125, "", f"Quileute Tribal Council fire department, call WQOM838, Ellis Mountain, input 465.2125; tone not published in ULS; {_ULS}"),
)

INTEROP: Sequence[ChannelRow] = (
    ("WA SAR VSAR16", 155.160, "", "NFM", _ST_EMS, None, "", f"Washington search and rescue common VSAR16, carrier squelch for receive; {_WAFOG}"),
    ("LERN", 155.370, "", "NFM", _ST_LAW, None, "", f"Law Enforcement Radio Network; WAFOG lists Striped Peak and Ellis Mountain sites for Clallam County; {_WAFOG}"),
    ("OSCCR", 156.135, "TONE=C203.5", "NFM", _ST_EMS, None, "", f"On-scene command and coordination; {_RR_MUTUAL_AID}"),
    ("REDNET", 153.830, "", "NFM", _ST_FIRE, None, "", f"Washington fire mutual aid REDNET; {_RR_MUTUAL_AID}"),
    ("WHEERS Medical", 463.000, "TONE=C179.9", "NFM", _ST_EMS, None, "", f"Washington state medical control WHEERS-1; {_RR_MUTUAL_AID}"),
    ("Fed Interop NC1", 169.5375, "TONE=C167.9", "NFM", _ST_OTHER, None, "", f"Federal interoperability NC1/IR5; {_RR_NAT_INTEROP}"),
    ("Fed Interop IR1", 170.0125, "", "NFM", _ST_OTHER, None, "", f"Federal interoperability IR1/IR6; {_RR_NAT_INTEROP}"),
    ("Fed Interop IR2", 170.4125, "", "NFM", _ST_OTHER, None, "", f"Federal interoperability IR2/IR7; {_RR_NAT_INTEROP}"),
    ("Fed Interop IR3", 170.6875, "", "NFM", _ST_OTHER, None, "", f"Federal interoperability IR3/IR8; {_RR_NAT_INTEROP}"),
    ("Fed Interop LE1", 167.0875, "TONE=C167.9", "NFM", _ST_LAW, None, "", f"Federal law enforcement interoperability LE1/LEA; {_RR_NAT_INTEROP}"),
    ("Fed SAR Incident Cmd", 410.8375, "", "NFM", _ST_EMS, None, "", f"Federal interoperability IR12, SAR incident command; {_RR_NAT_INTEROP}"),
    ("USCG Aux WA Repeater", 150.700, "", "NFM", _ST_MARINE, None, "", "US Coast Guard Auxiliary Washington state repeater; https://www.radioreference.com/db/aid/7760"),
    ("USCG Aux Yankee 3", 143.475, "", "NFM", _ST_MARINE, None, "", "US Coast Guard Auxiliary nationwide simplex Yankee 3; https://www.radioreference.com/db/aid/7760"),
)

MARINE: Sequence[ChannelRow] = (
    ("Marine 16 Distress", 156.800, "", "FM", _ST_MARINE, None, "", f"International hailing, calling and distress; {_RR_MARINE}"),
    ("Marine 22A USCG", 157.100, "", "FM", _ST_MARINE, None, "", f"US Coast Guard liaison and maritime safety broadcasts; {_RR_MARINE}"),
    ("Prince Rupert Traffic 74", 156.725, "", "FM", _ST_MARINE, None, "", f"Vessel traffic sector covering the water off Cape Alava, west of 124-40W; {_NAVCEN_VTS}"),
    ("Seattle Traffic 5A", 156.250, "", "FM", _ST_MARINE, None, "", f"Vessel traffic, Strait of Juan de Fuca east of 124-40W; {_NAVCEN_VTS}"),
    ("Marine 13 Bridge", 156.650, "", "FM", _ST_MARINE, None, "", f"Intership navigation safety, bridge to bridge; {_RR_MARINE}"),
    ("Marine 06 Safety", 156.300, "", "FM", _ST_MARINE, None, "", f"Intership safety; {_RR_MARINE}"),
    ("Marine 09 Calling", 156.450, "", "FM", _ST_MARINE, None, "", f"Boater calling; {_RR_MARINE}"),
    ("Victoria Traffic 11", 156.550, "", "FM", _ST_MARINE, None, "", f"Vessel traffic, Haro Strait and southern Strait of Georgia; {_NAVCEN_VTS}"),
    ("Seattle Traffic 14", 156.700, "", "FM", _ST_MARINE, None, "", f"Vessel traffic, Puget Sound and Hood Canal; {_NAVCEN_VTS}"),
    ("Marine 68", 156.425, "", "FM", _ST_MARINE, None, "", f"Non-commercial working; {_RR_MARINE}"),
    ("Marine 69", 156.475, "", "FM", _ST_MARINE, None, "", f"Non-commercial working; {_RR_MARINE}"),
    ("Marine 71", 156.575, "", "FM", _ST_MARINE, None, "", f"Non-commercial working; {_RR_MARINE}"),
    ("Marine 72", 156.625, "", "FM", _ST_MARINE, None, "", f"Non-commercial intership; {_RR_MARINE}"),
    ("Marine 21A USCG", 157.050, "", "FM", _ST_MARINE, None, "", f"US Coast Guard working; {_RR_MARINE}"),
    ("Marine 23A USCG", 157.150, "", "FM", _ST_MARINE, None, "", f"US Coast Guard working; {_RR_MARINE}"),
    ("Marine 83A USCG", 157.175, "", "FM", _ST_MARINE, None, "", f"US Coast Guard only; {_RR_MARINE}"),
    ("Marine 88A", 157.425, "", "FM", _ST_MARINE, None, "", f"Commercial intership bridge to bridge; {_RR_MARINE}"),
)

WEATHER: Sequence[ChannelRow] = (
    ("NOAA Neah Bay KIH36", 162.550, "", "FM", _ST_OTHER, None, "", f"NOAA weather radio KIH36, Bohokus Peak Neah Bay, primary at Ozette; {_NWS_STATIONS}"),
    ("NOAA Forks KXI27", 162.425, "", "FM", _ST_OTHER, None, "", f"NOAA weather radio KXI27, Clearwater near Forks; {_NWS_STATIONS}"),
)

AVIATION: Sequence[ChannelRow] = (
    ("ZSE Sector 03 Neah Bay", 125.100, "", "AM", _ST_AVIATION, None, "", f"Seattle Center sector 03, Neah Bay RCAG, the sector over Lake Ozette; {_RR_ZSE}"),
    ("CTAF Quillayute Forks Sekiu", 122.900, "", "AM", _ST_AVIATION, None, "", "Common traffic advisory for KUIL, S18 and 11S; https://www.airnav.com/airport/KUIL"),
    ("ASOS Quillayute", 135.225, "", "AM", _ST_AVIATION, None, "", "Automated weather at Quillayute State Airport KUIL; https://www.airnav.com/airport/KUIL"),
    ("Guard 121.5", 121.500, "", "AM", _ST_AVIATION, None, "", "International aeronautical emergency; https://www.airnav.com/airport/KNUW"),
    ("ZSE Sector 02 Hoquiam", 128.300, "", "AM", _ST_AVIATION, None, "", f"Seattle Center sector 02, Hoquiam RCAG, south Washington coast; {_RR_ZSE}"),
    ("ZSE Sector 12 Whidbey", 134.950, "", "AM", _ST_AVIATION, None, "", f"Seattle Center sector 12, Whidbey Island RCAG; {_RR_ZSE}"),
    ("ZSE Sector 01 Seattle", 120.300, "", "AM", _ST_AVIATION, None, "", f"Seattle Center sector 01; {_RR_ZSE}"),
    ("CG Ops Port Angeles", 127.700, "", "AM", _ST_AVIATION, None, "", "Coast Guard Air Station Port Angeles operations; https://www.airnav.com/airport/KNOW"),
    ("Whidbey Approach", 118.200, "", "AM", _ST_AVIATION, None, "", "NAS Whidbey Island approach and departure, west; https://www.airnav.com/airport/KNUW"),
    ("Port Angeles CTAF", 122.975, "", "AM", _ST_AVIATION, None, "", "Fairchild International KCLM common traffic advisory and UNICOM; https://www.airnav.com/airport/KCLM"),
    ("Port Angeles ASOS", 135.175, "", "AM", _ST_AVIATION, None, "", "Automated weather at KCLM; https://www.airnav.com/airport/KCLM"),
    ("Ediz Hook AWOS", 118.325, "", "AM", _ST_AVIATION, None, "", "Automated weather at Coast Guard Air Station Port Angeles KNOW; https://www.airnav.com/airport/KNOW"),
    ("Seattle Radio PA RCO", 122.600, "", "AM", _ST_AVIATION, None, "", "Seattle Radio flight service, Port Angeles remote outlet; https://www.airnav.com/airport/KCLM"),
    ("Whidbey Tower", 127.900, "", "AM", _ST_AVIATION, None, "", "NAS Whidbey Island tower; https://www.airnav.com/airport/KNUW"),
    ("Whidbey ATIS", 134.150, "", "AM", _ST_AVIATION, None, "", "NAS Whidbey Island automatic terminal information; https://www.airnav.com/airport/KNUW"),
    ("CG Air-Ground Secondary", 379.050, "", "AM", _ST_MILITARY, None, "", "US Coast Guard air-to-ground secondary; https://www.radioreference.com/db/aid/7760"),
    ("CGAS PA VFR Advisory", 381.800, "", "AM", _ST_MILITARY, None, "", "Coast Guard Air Station Port Angeles VFR advisory; https://www.airnav.com/airport/KNOW"),
)

TRANSPORT: Sequence[ChannelRow] = (
    ("MV Coho Loading", 461.1875, "TONE=C136.5", "NFM", _ST_TRANSPORT, None, "", f"Black Ball ferry MV Coho loading and offloading, Port Angeles to Victoria; {_RR_CLALLAM}"),
    ("MV Coho Bridge", 467.775, "D125", "NFM", _ST_TRANSPORT, None, "", f"Black Ball ferry MV Coho bridge to engine room; {_RR_CLALLAM}"),
    ("WA Ferries Deck Shore", 151.040, "", "NFM", _ST_TRANSPORT, None, "", "Washington State Ferries deck to shore, call KA3145; https://www.radioreference.com/db/aid/2299"),
    ("Bonneville Power", 172.525, "", "NFM", _ST_UTILITIES, None, "", f"Bonneville Power Administration repeater; {_RR_FED}"),
)

#: Amateur repeaters and simplex channels on the west peninsula.  Inputs and
#: tones are as published by RepeaterBook and the Washington Field Operations
#: Guide; nothing here is derived from a standard band-plan offset.
AMATEUR: Sequence[ChannelRow] = (
    ("Ellis Mtn W7FEL", 147.060, "TONE=C100", "FM", _ST_HAM, 147.660, "TONE=C100", f"Clallam Bay, Ellis Mountain, W7FEL; nearest 2 m machine to Ozette; {_WAFOG}"),
    ("Gunderson Mtn W7FEL", 145.210, "TONE=C100", "FM", _ST_HAM, 144.610, "TONE=C100", f"Forks, Gunderson Mountain, W7FEL; {_WAFOG}"),
    ("Mt Octopus K7PP", 147.280, "TONE=C123", "FM", _ST_HAM, 147.880, "TONE=C123", f"Forks, Mount Octopus, K7PP, high west peninsula site; {_REPEATERBOOK_CLALLAM}"),
    ("Striped Peak W7FEL", 146.760, "TONE=C100", "FM", _ST_HAM, 146.160, "TONE=C100", f"Port Angeles, Striped Peak, W7FEL, EchoLink; {_WAFOG}"),
    ("Port Angeles WF7W", 145.130, "TONE=C100", "FM", _ST_HAM, 144.530, "TONE=C100", f"Port Angeles, WF7W; {_REPEATERBOOK_CLALLAM}"),
    ("Carlsborg W7FEL", 146.760, "TONE=C77", "FM", _ST_HAM, 146.160, "TONE=C77", f"Carlsborg repeater sharing the Striped Peak pair on a different tone; {_WAFOG}"),
    ("Port Angeles 220 W6MPD", 224.060, "TONE=C107.2", "FM", _ST_HAM, 222.460, "TONE=C107.2", f"Port Angeles, W6MPD, 1.25 m; {_REPEATERBOOK_CLALLAM}"),
    ("Sequim Dungeness W7FEL", 441.125, "TONE=C100", "FM", _ST_HAM, 446.125, "TONE=C100", f"Sequim, Dungeness Heights, W7FEL; {_REPEATERBOOK_CLALLAM}"),
    ("Sequim Bell Hill KO6I", 442.050, "TONE=C103.5", "FM", _ST_HAM, 447.050, "TONE=C103.5", f"Sequim, Bell Hill, KO6I, EchoLink; {_REPEATERBOOK_CLALLAM}"),
    ("Sequim Blyn Mtn N7NFY", 442.800, "TONE=C123", "FM", _ST_HAM, 447.800, "TONE=C123", f"Sequim, Blyn Mountain, N7NFY; {_REPEATERBOOK_CLALLAM}"),
    ("Quilcene Buck Mtn W2ZT", 442.500, "TONE=C123", "FM", _ST_HAM, 447.500, "TONE=C123", f"Quilcene, Buck Mountain, W2ZT; {_REPEATERBOOK_CLALLAM}"),
    ("Forks Simplex", 147.500, "", "FM", _ST_HAM, None, "", f"Clallam County AUXCOMM 2 m simplex, Forks; {_WAFOG}"),
    ("North Coast Simplex", 147.420, "", "FM", _ST_HAM, None, "", f"Clallam County AUXCOMM 2 m simplex, north coast; {_WAFOG}"),
    ("Joyce Simplex", 147.540, "", "FM", _ST_HAM, None, "", f"Clallam County AUXCOMM 2 m simplex, Joyce; {_WAFOG}"),
    ("OP Area Central Simplex", 147.520, "", "FM", _ST_HAM, None, "", f"Clallam County AUXCOMM 2 m simplex, operational area central; {_WAFOG}"),
    ("West UHF Simplex", 439.600, "", "FM", _ST_HAM, None, "", f"Clallam County AUXCOMM 70 cm simplex, west; {_WAFOG}"),
    ("North Coast UHF Simplex", 439.550, "", "FM", _ST_HAM, None, "", f"Clallam County AUXCOMM 70 cm simplex, north coast; {_WAFOG}"),
    ("2m Calling", 146.520, "", "FM", _ST_HAM, None, "", "National 2 m FM simplex calling channel"),
    ("70cm Calling", 446.000, "", "FM", _ST_HAM, None, "", "National 70 cm FM simplex calling channel"),
    ("1.25m Calling", 223.500, "", "FM", _ST_HAM, None, "", "National 1.25 m FM simplex calling channel"),
)

_CFR_FRS_GMRS = "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-95"

#: FRS/GMRS shared and GMRS-only channels.  Channels 8-14 are FRS-only
#: interstitials: a GMRS licence does not authorize transmitting there, so
#: they are carried for listening and the plan keeps them receive-only.
GMRS_FRS: Sequence[ChannelRow] = tuple(
    (f"GMRS {n}", freq, "", "FM", _ST_BUSINESS, None, "", note)
    for n, freq, note in (
        (1, 462.5625, f"FRS/GMRS channel 1, shared; {_CFR_FRS_GMRS}"),
        (2, 462.5875, f"FRS/GMRS channel 2, shared; {_CFR_FRS_GMRS}"),
        (3, 462.6125, f"FRS/GMRS channel 3, shared; {_CFR_FRS_GMRS}"),
        (4, 462.6375, f"FRS/GMRS channel 4, shared; {_CFR_FRS_GMRS}"),
        (5, 462.6625, f"FRS/GMRS channel 5, shared; {_CFR_FRS_GMRS}"),
        (6, 462.6875, f"FRS/GMRS channel 6, shared; {_CFR_FRS_GMRS}"),
        (7, 462.7125, f"FRS/GMRS channel 7, shared; {_CFR_FRS_GMRS}"),
    )
) + tuple(
    (f"FRS {n}", freq, "", "NFM", _ST_BUSINESS, None, "", f"FRS-only interstitial channel {n}; not authorized for GMRS transmit; {_CFR_FRS_GMRS}")
    for n, freq in (
        (8, 467.5625), (9, 467.5875), (10, 467.6125), (11, 467.6375),
        (12, 467.6625), (13, 467.6875), (14, 467.7125),
    )
) + tuple(
    (f"GMRS {n}", freq, "", "FM", _ST_BUSINESS, None, "", f"GMRS main channel {n}, licence required; {_CFR_FRS_GMRS}")
    for n, freq in (
        (15, 462.5500), (16, 462.5750), (17, 462.6000), (18, 462.6250),
        (19, 462.6500), (20, 462.6750), (21, 462.7000), (22, 462.7250),
    )
) + tuple(
    (f"GMRS RPT{n}", freq, "", "FM", _ST_BUSINESS, freq + 5.0, "", f"GMRS repeater channel {n}, input {freq + 5.0:.4f}; no repeater is publicly published in Clallam County, so no access tone is set; {_CFR_FRS_GMRS}")
    for n, freq in (
        (15, 462.5500), (16, 462.5750), (17, 462.6000), (18, 462.6250),
        (19, 462.6500), (20, 462.6750), (21, 462.7000), (22, 462.7250),
    )
)

MURS: Sequence[ChannelRow] = tuple(
    (f"MURS {n}", freq, "", mode, _ST_BUSINESS, None, "", f"Multi-Use Radio Service channel {n}, no licence required; {_CFR_FRS_GMRS}")
    for n, freq, mode in (
        (1, 151.820, "NFM"), (2, 151.880, "NFM"), (3, 151.940, "NFM"),
        (4, 154.570, "FM"), (5, 154.600, "FM"),
    )
)

_DEPARTMENTS: Sequence[Tuple[str, Sequence[ChannelRow]]] = (
    ("Olympic NP and Forest", NPS_USFS),
    ("WA DNR Olympic Region", DNR),
    ("Clallam County", CLALLAM),
    ("Tribal Neah Bay and La Push", TRIBAL),
    ("SAR and Interop", INTEROP),
    ("Marine and Vessel Traffic", MARINE),
    ("NOAA Weather", WEATHER),
    ("Aviation", AVIATION),
    ("Ferry Transport Utility", TRANSPORT),
    ("Amateur West Peninsula", AMATEUR),
    ("GMRS and FRS", GMRS_FRS),
    ("MURS", MURS),
)


def _channel(row: ChannelRow, department: str) -> Channel:
    label, freq, tone, mode, service_type, tx_freq, tx_tone, note = row
    return Channel(
        id=stable_id(f"olympic-coast:{department}:{label}:{freq}", kind="channel"),
        label=label,
        freq_mhz=freq,
        mode=mode,
        tone=tone,
        service_type=service_type,
        notes=note,
        tx_freq_mhz=tx_freq,
        tx_tone=tx_tone,
    )


def _department(name: str, rows: Sequence[ChannelRow]) -> Department:
    return Department(
        id=stable_id(f"olympic-coast:dept:{name}", kind="department"),
        label=name,
        channels=[_channel(row, name) for row in rows],
        lat=OZETTE_LAT,
        lon=OZETTE_LON,
        range_miles=OZETTE_RANGE_MILES,
        shape="Circle",
    )


def system() -> System:
    departments = [_department(name, rows) for name, rows in _DEPARTMENTS]
    return System(
        id=stable_id("olympic-coast:system", kind="system"),
        label="Lake Ozette and NW Olympic Coast",
        departments=departments,
    )


def favorite() -> FavoritesList:
    """The ``OZ01`` Favorites List."""
    return FavoritesList(
        id=stable_id("olympic-coast:OZ01", kind="favorites-list"),
        slug="oz01",
        favorite_key="OZ01",
        favorite_name="Lake Ozette & NW Olympic Coast",
        region="NW Olympic Peninsula / Pacific Coast",
        counties="Clallam, Jefferson",
        scenario="Backcountry safety, wildland fire, marine, aviation and local public safety around Lake Ozette",
        source_type="conventional analog, individually cited",
        system_or_category="Lake Ozette and NW Olympic Coast structured channel set",
        sites_or_coverage=(
            f"USGS GNIS Ozette Lake {OZETTE_LAT:.6f},{OZETTE_LON:.6f} "
            f"(feature 1531490); Cape Alava {CAPE_ALAVA_LAT:.6f},{CAPE_ALAVA_LON:.6f} "
            f"(feature 1503792); {OZETTE_RANGE_MILES:g}-mile department radius"
        ),
        departments_or_channels=(
            "Olympic NP and NF; WA DNR Olympic Region including the Ozette repeater; "
            "Clallam County west dispatch; Makah and Quileute tribal repeaters; "
            "WA SAR and interop; marine and vessel traffic; NOAA weather; "
            "Seattle Center sector 03; amateur repeaters; GMRS/FRS and MURS"
        ),
        mode="FM/NFM analog and AM aviation",
        monitorability=(
            "Analog only. Clallam County trunked systems, USCG land mobile and "
            "federal law enforcement in this area are P25 and are deliberately excluded."
        ),
        upgrade_required="None",
        source_url=NPS_OZETTE_URL,
        notes=(
            "Every channel carries its own source in the channel note. Repeater inputs "
            "come from FCC ULS licence records or published coordination data, never "
            "from a band-plan offset. Tones absent from a licence record are left empty."
        ),
        systems=[system()],
    )


def favorites() -> List[FavoritesList]:
    return [favorite()]
