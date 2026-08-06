"""Palette-independent listening packs built from verified catalog components.

Favorites Lists scan discrete programmed channels, not every frequency in a
continuous allocation. These packs therefore reuse the project's cited,
monitorable channels by listening scenario; ``docs/band-scanning.md`` supplies
matching SDS150 Custom Search ranges for exploratory band sweeps.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import FavoritesList
from wasds150.util.hashing import stable_id


def _band(
    number: int,
    name: str,
    scenario: str,
    components: str,
    coverage: str,
    content: str,
    mode: str,
    source_url: str,
    notes: str,
) -> FavoritesList:
    key = f"BAND{number:02d}"
    return FavoritesList(
        id=stable_id(f"band-profile:{key}", kind="favorites-list"),
        slug=key.lower(),
        favorite_key=key,
        favorite_name=name,
        region="Washington / Pacific Northwest",
        counties="All 39 counties",
        scenario=scenario,
        source_type="derived verified rollup",
        system_or_category=f"Band listening pack (reuses {components})",
        sites_or_coverage=coverage,
        departments_or_channels=content,
        mode=mode,
        monitorability="Verified clear/reference components; data-only and encrypted traffic may be silent",
        upgrade_required="DMR/NXDN only where a reused component explicitly requires it",
        source_url=source_url,
        notes=notes,
    )


def favorites() -> List[FavoritesList]:
    return [
        _band(1, "Band - Civil Air", "Civil aviation band listening", "FL44, FL46, FL47, FL48, FL55, FL74a",
              "Statewide airports, en-route sectors, guard, SAR and airshow channels",
              "Tower/ground/approach, CTAF, ARTCC/FSS, 121.5 guard, SAR/medevac and event air channels",
              "AM", "https://www.faa.gov/air_traffic/publications/",
              "Use Custom Search 118.000-136.975 MHz AM to discover nearby active assignments."),
        _band(2, "Band - Military Air", "Military aviation band listening", "FL44, FL48, FL49, FL52, FL59, FL73",
              "Statewide military training airspace and Pacific Northwest bases",
              "243.0 guard, published JBLM/Whidbey/Fairchild/CAP, USCG air and airshow channels",
              "AM + P25/FM where verified", "https://www.faa.gov/air_traffic/publications/",
              "Use Custom Search 225.000-399.975 MHz AM; frequency agility and encryption limit reception."),
        _band(3, "Band - Amateur VHF/UHF", "Amateur radio band listening", "FL51, FL60, FL61, FL62, FL63",
              "Statewide repeaters, linked systems, emergency nets, simplex and satellites",
              "6m/2m/1.25m/70cm calling, analog repeaters, ARES/RACES/ACS, ISS and FM satellites",
              "FM + DMR where verified", "https://www.arrl.org/band-plan",
              "SDS150 has no SSB demodulation; prioritize FM calling/repeater segments and local coordinated repeaters."),
        _band(4, "Band - Marine VHF", "Marine band listening", "FL52, FL53, FL54, FL55",
              "Puget Sound, Hood Canal, coast and Columbia River",
              "USCG/VTS, Ch16 distress, Ch13 bridge, Ch22A liaison, ferry, port and rescue aviation",
              "FM + AM/P25 where verified", "https://www.navcen.uscg.gov/us-vhf-channel-information",
              "AIS 161.975/162.025 is data-only and intentionally not treated as voice."),
      _band(5, "Band - Railroad", "Railroad band listening", "FL56, FL57",
              "Western/eastern mainlines, yards, shortlines and Sounder",
              "AAR road, dispatch, yard and maintenance channels plus transit-rail operations",
              "NFM + P25/NXDN where verified", "https://www.radioreference.com/db/aid/9298",
              "Use Custom Search 159.810-161.565 MHz NFM; NXDN carriers require the paid upgrade for voice."),
        _band(6, "Band - Personal & Itinerant", "Personal/business short-range listening", "FL65, FL66, FL68",
              "Statewide; typically local line-of-sight reception",
              "FRS/GMRS, MURS, CB, business color-dot and itinerant channels",
              "FM/NFM + AM", "https://www.ecfr.gov/current/title-47/chapter-I/subchapter-D/part-95",
              "High local activity potential around trailheads, events, construction and travel corridors."),
        _band(7, "Band - Public Safety Interop", "Public-safety interoperability listening", "FL01, FL02, FL03, FL06, FL07",
              "Statewide and incident-deployed interoperability",
              "SAR/mutual aid, CEMNET, NIFOG VHF/UHF/700/800, WA STATEOPS, DNR and NIFC",
              "FM/NFM + P25", "https://www.cisa.gov/sites/default/files/2024-12/NIFOG%202.02_508%20FINAL%20VERSION%2012%2003%202024.pdf",
              "Current post-rebanding receive/output channels; monitor during incidents and exercises."),
        _band(8, "Band - Weather, SAR & Emergency", "Emergency and severe-weather listening", "FL01, FL03, FL44, FL55, FL71, FL75",
              "Statewide terrestrial, aviation and NOAA Weather coverage",
              "NOAA Weather, SAR, CEMNET, guard, medevac, HEAR/MED and rescue aviation",
              "WX + FM + AM/P25", "https://www.weather.gov/nwr/stations?State=WA",
              "Enable Weather Alert Priority separately; SAME alerting is configured by county in Sentinel."),
        _band(9, "Band - Federal Wildland & Parks", "Federal outdoor/wildland listening",
              "FL06, FL07, FL32, FL33, FL34, FL35, FL36, FL37, FL38, FL39, FL40, FL41, FL42, FL43, FL44",
              "Washington national forests, national parks, wilderness and wildfire incidents",
              "NPS/USFS, NIFC, DNR, SAR, aviation guard and incident command channels",
              "FM/NFM + AM", "https://www.nps.gov/olym/planyourvisit/wilderness-safety.htm",
              "Federal assignments can be repeater/site dependent; incident tactical channels vary by assignment."),
        _band(10, "Band - Medical & Medevac", "Medical/EMS listening", "FL44, FL55, FL70b, FL71",
              "Statewide hospitals, EMS coordination and air-medical bases",
              "HEAR/MED, Airlift/Life Flight, hospital coordination and AMR NXDN",
              "FM + AM + P25/NXDN", "https://mil.wa.gov/asset/610097d704789",
              "NXDN entries require the paid upgrade; patient information may be limited or protected."),
        _band(11, "Band - Roads, Rail & Utilities", "Transportation and infrastructure listening", "FL53, FL56, FL57, FL69, FL74b",
              "Statewide highways, ferries, railroads and utility territories",
              "WSDOT conventional, tow/road crews, ferry channels, AAR rail and utility voice",
              "FM/NFM + P25 where verified", "https://wsdot.wa.gov/travel/operations-services/emergency-operations",
              "SCADA and telemetry are data-only; this pack emphasizes decodable voice components."),
        _band(12, "Band - Business, Events & Media", "Business/event listening", "FL68, FL70a, FL70b, FL73, FL74a",
              "Urban/suburban businesses, transit bases, fairs, airshows and field media",
              "Color-dot/itinerant, commercial DMR/NXDN, event UHF, air boss and ENG coordination",
              "FM/NFM + AM + DMR/NXDN", "https://www.fcc.gov/wireless/bureau-divisions/mobility-division/industrial-business",
              "Use Close Call near venues; temporary and leased event assignments change."),
    ]
