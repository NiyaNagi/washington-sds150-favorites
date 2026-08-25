"""HF nets, utility stations and beacons worth having in a memory.

Scope and why it is drawn where it is
-------------------------------------
:mod:`wasds150.catalog.ham_bandplan` already covers the *band plan*: calling
frequencies, digital watering holes, QRP centres. What it deliberately does
not cover is the two things an operator actually tunes to when the band is
open and nothing is happening on the calling frequency:

* long-running **nets** - somewhere a conversation is reliably taking place;
* **utility** stations - marine, aeronautical, military and time signals,
  which are on the air continuously and make excellent propagation checks.

A note on how much of this to trust
-----------------------------------
Net **frequencies** are remarkably stable: the Maritime Mobile Service Net has
been on 14.300 for decades. Net **schedules** are not. Clubs move times,
seasons shift, nets fold quietly. Times are therefore recorded in the notes as
context rather than as fact, and every net channel says so.

Utility allocations are the opposite: they are regulated assignments (ITU
appendix 17 for marine, ICAO regional plans for aeronautical, published DoD
frequencies for HFGCS) and change on a scale of decades.

Everything here is **receive-oriented**. Transmitting into a net requires
knowing its protocol and, on the emergency nets, being asked. A channel plan
decides whether transmit is enabled; this module only says what is there.
"""
from __future__ import annotations

from typing import List

from wasds150.models.catalog import Channel, Department, FavoritesList, System
from wasds150.models.provenance import Provenance
from wasds150.util.hashing import stable_id

FAVORITE_KEY = "HFNET01"
SLUG = "hf-nets-and-utility"

#: Sources. These are the organisations that run the nets and the agencies
#: that hold the utility allocations, not aggregator sites, because an
#: aggregator's copy goes stale without anyone noticing.
MMSN_URL = "https://www.mmsn.org/"
HWN_URL = "https://www.hwn.org/"
SATERN_URL = "https://www.satern.org/"
ARRL_NTS_URL = "https://www.arrl.org/nts"
IARU_R2_URL = "https://www.iaru-r2.org/en/reference/band-plan/"
NCDXF_BEACON_URL = "https://www.ncdxf.org/beacon/"
HFGCS_URL = "https://www.tinker.af.mil/HFGCS/"
NOAA_MARINE_URL = "https://www.weather.gov/marine/hfvoice"
USCG_URL = "https://www.navcen.uscg.gov/marine-communications"
NIST_URL = "https://www.nist.gov/pml/time-and-frequency-division/time-distribution/radio-station-wwv"
ICAO_HF_URL = "https://www.faa.gov/air_traffic/publications/atpubs/aip_html/"

#: Amateur service. Matches what the rest of the catalog uses for ham entries.
SERVICE_AMATEUR = 13


def _channel(
    label: str,
    freq_mhz: float,
    mode: str,
    notes: str,
    *,
    service_type: int = SERVICE_AMATEUR,
    priority: bool = False,
) -> Channel:
    return Channel(
        id=stable_id(f"hf-nets:{label}:{freq_mhz}", kind="channel"),
        label=label,
        freq_mhz=freq_mhz,
        mode=mode,
        service_type=service_type,
        priority=priority,
        notes=notes,
    )


def _schedule_caveat(text: str) -> str:
    return f"{text} Schedule changes; confirm with the net before relying on it."


def _emergency_nets() -> List[Channel]:
    """Nets that activate for weather and emergencies.

    Worth having programmed precisely because you want them *before* the event,
    not while looking them up during one.
    """
    return [
        _channel(
            "Maritime Mobile Svc Net", 14.300, "USB",
            _schedule_caveat(
                "MMSN: safety and welfare traffic for vessels at sea, daily "
                "roughly 1600-0200 UTC. Also an IARU Region 2 emergency centre "
                f"of activity. {MMSN_URL}"
            ),
            priority=True,
        ),
        _channel(
            "Hurricane Watch Net 20m", 14.325, "USB",
            _schedule_caveat(
                "HWN: activates when a hurricane threatens land, relaying "
                f"ground truth to the National Hurricane Center. {HWN_URL}"
            ),
            priority=True,
        ),
        _channel(
            "Hurricane Watch Net 40m", 7.268, "LSB",
            _schedule_caveat(
                f"HWN night-time frequency; shares 7.268 with the Waterway Net. {HWN_URL}"
            ),
        ),
        _channel(
            "SATERN 20m", 14.265, "USB",
            _schedule_caveat(
                "Salvation Army Team Emergency Radio Network: health and "
                f"welfare enquiries during disasters. {SATERN_URL}"
            ),
        ),
        _channel(
            "Waterway Net", 7.268, "LSB",
            _schedule_caveat(
                "Cruising boats in the Caribbean and western Atlantic reporting "
                "position and weather, mornings around 1145 UTC."
            ),
        ),
        _channel(
            "Pacific Seafarers Net", 14.300, "USB",
            _schedule_caveat(
                "Position reporting for vessels crossing the Pacific, around "
                "0300 UTC. Shares 14.300 with MMSN."
            ),
        ),
    ]


def _centres_of_activity() -> List[Channel]:
    """IARU Region 2 emergency centres of activity.

    Not nets: these are the frequencies the region agrees to keep clear and
    listen on when something happens. Useful to have when a band is otherwise
    quiet, because activity here means something is going on.
    """
    note = (
        "IARU Region 2 emergency centre of activity - kept clear for disaster "
        f"traffic. {IARU_R2_URL}"
    )
    return [
        _channel("EmCOA 80m", 3.750, "LSB", note),
        _channel("EmCOA 40m", 7.240, "LSB", note),
        _channel("EmCOA 20m", 14.300, "USB", note),
        _channel("EmCOA 17m", 18.160, "USB", note),
        _channel("EmCOA 15m", 21.360, "USB", note),
    ]


def _traffic_and_ragchew() -> List[Channel]:
    """Long-running nets that are simply reliable places to hear people."""
    return [
        _channel(
            "Noontime Net", 7.2835, "LSB",
            _schedule_caveat(
                "West coast check-in net running since the 1960s, mid-day "
                "Pacific. One of the most dependable places to gauge 40m "
                "conditions from the Pacific Northwest."
            ),
            priority=True,
        ),
        _channel(
            "3905 Century Club 80m", 3.905, "LSB",
            _schedule_caveat(
                "Nightly county-hunting and QSL net; a good propagation gauge "
                "on 80m after dark."
            ),
        ),
        _channel(
            "3905 Century Club 40m", 7.208, "LSB",
            _schedule_caveat("Evening session of the same club."),
        ),
        _channel(
            "County Hunters 20m", 14.336, "USB",
            _schedule_caveat("Mobile operators working US counties; daily, daylight hours."),
        ),
        _channel(
            "County Hunters 40m CW", 7.0560, "CW",
            _schedule_caveat("CW side of county hunting."),
        ),
        _channel(
            "NTS Region 6 40m", 7.2320, "LSB",
            _schedule_caveat(
                "Regional National Traffic System cycle covering the western "
                f"states. {ARRL_NTS_URL}"
            ),
        ),
        _channel(
            "Western Public Service Net", 3.9520, "LSB",
            _schedule_caveat(
                "Evening health-and-welfare and traffic net for the western "
                "states, on or near 3.952."
            ),
        ),
    ]


def _pacific_northwest() -> List[Channel]:
    """Regional nets.

    Regional net frequencies drift more than national ones - a section net may
    move a few kHz to dodge interference and never update its web page. Treat
    these as starting points and tune either side.
    """
    return [
        _channel(
            "WA Traffic Net 80m", 3.5670, "CW",
            _schedule_caveat(
                "Washington State Net, CW traffic handling, evenings. Tune "
                "either side; section nets move to dodge QRM."
            ),
        ),
        _channel(
            "WA Traffic Net Phone", 3.9670, "LSB",
            _schedule_caveat("Washington phone traffic net, evenings."),
        ),
        _channel(
            "Oregon Section Net", 3.9800, "LSB",
            _schedule_caveat("Oregon ARRL section traffic net, evenings."),
        ),
        _channel(
            "Idaho Montana Net", 3.9350, "LSB",
            _schedule_caveat("Inland northwest section traffic."),
        ),
        _channel(
            "PNW ARES 75m", 3.9850, "LSB",
            _schedule_caveat(
                "Regional ARES/RACES coordination frequency used across the "
                "Pacific Northwest during exercises and activations."
            ),
        ),
    ]


def _utility_hf() -> List[Channel]:
    """Non-amateur HF that is always on and therefore always useful.

    These are the best propagation beacons available: a station you can hear
    at a known power from a known place tells you more about the band than any
    prediction. Receive only - none of these may be transmitted on.
    """
    aero = (
        "Oceanic air traffic control, ICAO regional plan. Continuous position "
        f"reports; an excellent long-path propagation check. Receive only. {ICAO_HF_URL}"
    )
    hfgcs = (
        "US Air Force High Frequency Global Communications System. Continuous "
        f"carrier with EAM broadcasts. Receive only. {HFGCS_URL}"
    )
    marine = (
        "US Coast Guard / NOAA high seas voice and weather broadcast. "
        f"Receive only. {NOAA_MARINE_URL}"
    )
    return [
        # Aeronautical - San Francisco and Oakland oceanic, the ones audible
        # from the Pacific Northwest.
        _channel("SFO Oceanic 5.547", 5.547, "USB", aero, service_type=1),
        _channel("SFO Oceanic 8.843", 8.843, "USB", aero, service_type=1),
        _channel("SFO Oceanic 10.057", 10.057, "USB", aero, service_type=1),
        _channel("SFO Oceanic 13.288", 13.288, "USB", aero, service_type=1),
        _channel("SFO Oceanic 17.904", 17.904, "USB", aero, service_type=1),
        # HFGCS - always on, easy to hear, good signal-strength reference.
        _channel("HFGCS 4.724", 4.724, "USB", hfgcs, service_type=1),
        _channel("HFGCS 6.739", 6.739, "USB", hfgcs, service_type=1),
        _channel("HFGCS 8.992", 8.992, "USB", hfgcs, service_type=1),
        _channel("HFGCS 11.175", 11.175, "USB", hfgcs, service_type=1, priority=True),
        _channel("HFGCS 15.016", 15.016, "USB", hfgcs, service_type=1),
        # Marine high seas.
        _channel("USCG Pacific 4.426", 4.426, "USB", marine, service_type=1),
        _channel("USCG Pacific 8.764", 8.764, "USB", marine, service_type=1),
        _channel("USCG Pacific 13.089", 13.089, "USB", marine, service_type=1),
        _channel(
            "Marine Distress 2182", 2.182, "USB",
            f"International maritime distress and calling. Receive only. {USCG_URL}",
            service_type=1,
        ),
    ]


def _beacons() -> List[Channel]:
    """Propagation beacons.

    The NCDXF/IARU network is eighteen stations worldwide transmitting in turn
    on five frequencies, three minutes per cycle. Hearing which stations come
    through tells you where a band is open right now, which no prediction can.
    """
    note = (
        "NCDXF/IARU international beacon network: 18 stations rotating, 10 s "
        f"each, 3 min cycle. Tells you where the band is actually open. {NCDXF_BEACON_URL}"
    )
    return [
        _channel("NCDXF Beacon 20m", 14.100, "CW", note, priority=True),
        _channel("NCDXF Beacon 17m", 18.110, "CW", note),
        _channel("NCDXF Beacon 15m", 21.150, "CW", note),
        _channel("NCDXF Beacon 12m", 24.930, "CW", note),
        _channel("NCDXF Beacon 10m", 28.200, "CW", note),
    ]


def _time_standards() -> List[Channel]:
    """Time and frequency standards.

    Known transmitter, known power, known location. The cleanest possible
    check on whether a band is open and on the receiver's own calibration.
    """
    wwv = (
        "NIST WWV Fort Collins CO / WWVH Kauai HI. Continuous time and "
        f"frequency standard; propagation and calibration reference. {NIST_URL}"
    )
    return [
        _channel("WWV 2.5", 2.500, "AM", wwv, service_type=1),
        _channel("WWV 5", 5.000, "AM", wwv, service_type=1),
        _channel("WWV 10", 10.000, "AM", wwv, service_type=1, priority=True),
        _channel("WWV 15", 15.000, "AM", wwv, service_type=1),
        _channel("WWV 20", 20.000, "AM", wwv, service_type=1),
        _channel("WWV 25", 25.000, "AM", wwv, service_type=1),
    ]


def _six_metre() -> List[Channel]:
    """6 m - the magic band.

    Included because it behaves like nothing else: dead for weeks, then
    suddenly open to the other side of the country on sporadic E. The calling
    frequencies are where that gets noticed first.
    """
    return [
        _channel(
            "6m SSB Calling", 50.125, "USB",
            "National SSB calling frequency. First place an opening shows up.",
            priority=True,
        ),
        _channel("6m CW Calling", 50.090, "CW", "National CW calling frequency."),
        _channel(
            "6m FT8", 50.313, "USB",
            "FT8 watering hole. Often the only sign a marginal opening exists.",
            priority=True,
        ),
        _channel("6m FT8 DX", 50.323, "USB", "Secondary FT8 frequency used for DX."),
        _channel(
            "6m Beacons", 50.070, "CW",
            "Beacon sub-band, roughly 50.060-50.080. Listen here to catch an "
            "opening before anyone is calling.",
        ),
        _channel("6m FM Calling", 52.525, "FM", "National FM simplex calling frequency."),
    ]


def favorites() -> List[FavoritesList]:
    """The HF listening list, as one Favorites List."""
    departments = [
        Department(
            id=stable_id("hf-nets:emergency", kind="department"),
            label="HF Emergency and Weather Nets",
            channels=_emergency_nets(),
        ),
        Department(
            id=stable_id("hf-nets:emcoa", kind="department"),
            label="HF Emergency Centres of Activity",
            channels=_centres_of_activity(),
        ),
        Department(
            id=stable_id("hf-nets:traffic", kind="department"),
            label="HF Traffic and Calling Nets",
            channels=_traffic_and_ragchew(),
        ),
        Department(
            id=stable_id("hf-nets:pnw", kind="department"),
            label="HF Pacific Northwest Nets",
            channels=_pacific_northwest(),
        ),
        Department(
            id=stable_id("hf-nets:utility", kind="department"),
            label="HF Utility and Aeronautical",
            channels=_utility_hf(),
        ),
        Department(
            id=stable_id("hf-nets:beacons", kind="department"),
            label="HF Propagation Beacons",
            channels=_beacons(),
        ),
        Department(
            id=stable_id("hf-nets:time", kind="department"),
            label="Time and Frequency Standards",
            channels=_time_standards(),
        ),
        Department(
            id=stable_id("hf-nets:six-metre", kind="department"),
            label="6 Meter Calling and Beacons",
            channels=_six_metre(),
        ),
    ]

    system = System(
        id=stable_id("hf-nets:system", kind="system"),
        label="HF Nets, Utility and Beacons",
        departments=departments,
    )

    favorite = FavoritesList(
        id=stable_id(f"hf-nets:{FAVORITE_KEY}", kind="favorite"),
        slug=SLUG,
        favorite_key=FAVORITE_KEY,
        favorite_name="HF Nets, Utility and Beacons",
        region="HF - worldwide, with Pacific Northwest regional nets",
        counties="",
        scenario="Tuning HF: somewhere to go when the calling frequency is quiet",
        source_type="Published net and agency frequency lists",
        system_or_category="Amateur HF nets, utility HF, beacons, time standards",
        sites_or_coverage="Skywave; coverage varies with band and time of day",
        departments_or_channels=(
            "Emergency and weather nets, IARU emergency centres of activity, "
            "traffic and calling nets, Pacific Northwest section nets, "
            "aeronautical and marine utility, HFGCS, NCDXF beacons, WWV/WWVH "
            "time standards, and the 6 m calling frequencies."
        ),
        mode="SSB, CW and AM; receive-oriented",
        monitorability="Fully monitorable with an HF receiver",
        upgrade_required="None",
        source_url=MMSN_URL,
        notes=(
            "Net frequencies are stable over decades; net schedules are not. "
            "Times in the channel notes are context, not fact - confirm with "
            "the net before depending on one. Utility and beacon entries are "
            "regulated allocations and change far more slowly. Transmitting "
            "requires the relevant licence privileges, and on the utility "
            "channels is not permitted at all."
        ),
        systems=[system],
        # Most of this list is below 25 MHz or uses SSB/CW, neither of which
        # an SDS150 can do. That is not a data error - it is content for a
        # different radio - so the row is marked reference only and the
        # scanner's exporter projects it away instead of refusing to build.
        reference_only=True,
        provenance=[
            Provenance(source_adapter="operator_pages", source_url=MMSN_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=HWN_URL, confidence="verified"),
            Provenance(source_adapter="operator_pages", source_url=SATERN_URL, confidence="community"),
            Provenance(source_adapter="operator_pages", source_url=ARRL_NTS_URL, confidence="community"),
            Provenance(source_adapter="iaru", source_url=IARU_R2_URL, confidence="verified"),
            Provenance(source_adapter="ncdxf", source_url=NCDXF_BEACON_URL, confidence="verified"),
            Provenance(source_adapter="usaf", source_url=HFGCS_URL, confidence="verified"),
            Provenance(source_adapter="noaa", source_url=NOAA_MARINE_URL, confidence="verified"),
            Provenance(source_adapter="uscg_navcen", source_url=USCG_URL, confidence="verified"),
            Provenance(source_adapter="nist", source_url=NIST_URL, confidence="verified"),
        ],
    )
    return [favorite]

