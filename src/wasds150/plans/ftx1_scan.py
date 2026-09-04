"""FTX-1 - one scannable list for everything tunable within 75 miles.

``ftx1-local`` splits the same content into eighteen service blocks. This plan
answers a blunter request: *put everything I can hear from home into a single
memory list, in frequency order, so pressing the scan button sweeps every band
at once.*

The consequences:

**One ascending run.** The repeater bands, simplex calling, HF voice nets and
the receive-only public-service channels are emitted as a small number of
frequency-sorted blocks that butt up against each other, so a plain memory
scan walks 1.8 MHz to 470 MHz in order without the operator choosing a bank.

**Data and reference channels are programmed but locked out of the sweep.**
HF digital watering holes, propagation beacons, WWV and the HF utility
channels carry continuous carriers that would park the scan on every pass, so
they are ``skip_scan`` - present to tune by hand, invisible to the sweep.

**Repeaters are filtered by real distance.** Every WWARA machine carries its
own coordinates; the selector keeps only those within :data:`RADIUS_MILES` of
:data:`HOME`, so the list follows the home location rather than a region.
Lapsed coordinations are excluded, and modes this radio cannot demodulate
(DMR, D-STAR, Fusion, P25) are dropped during resolution with the reason
stated.
"""
from __future__ import annotations

from wasds150.models.plan import (
    SORT_FREQ,
    TX_NONE,
    TX_REPEATER,
    TX_SIMPLEX,
    ChannelPlan,
    ChannelSelector,
    PlanBlock,
)

#: 28523 NE 30th Ct, Redmond WA 98053 (Union Hill / Redmond Ridge). Change
#: these two numbers and re-export to rebuild the list around somewhere else.
HOME = (47.6351, -121.9954)

#: A 50-mile working range plus 25 miles of headroom: WWARA fuzzes some
#: transmitter sites by up to ~50 miles, and a well-sited foothill repeater is
#: workable well past 50. An extra channel is a nuisance; a missing local
#: machine is a gap you find when you need it.
RADIUS_MILES = 75.0

_WITHIN = (HOME[0], HOME[1], RADIUS_MILES)


def _near(*keys: str, dept: str = "", labels: str = "", exclude: str = "") -> ChannelSelector:
    """A selector that also requires the channel's own site to be inside the
    radius. Channels with no coordinates are dropped, which is the point."""
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
        within_miles=_WITHIN,
    )


def _sel(*keys: str, dept: str = "", labels: str = "", exclude: str = "") -> ChannelSelector:
    """An ordinary selector, for content with no meaningful position - HF and
    the band plan are propagation-dependent and belong to no place."""
    return ChannelSelector(
        favorite_keys=tuple(keys),
        department_pattern=dept,
        label_pattern=labels,
        exclude_label_pattern=exclude,
    )


FTX1_SCAN = ChannelPlan(
    id="ftx1-scan",
    radio_id="ftx1",
    label="FTX-1 - One-List Scan (75 mi)",
    description=(
        "Everything the FTX-1 can tune within 75 miles of home, as a single "
        "frequency-ordered memory list: coordinated 6 m / 2 m / 70 cm "
        "repeaters, simplex calling, HF voice nets and calling, and weather / "
        "marine / air / GMRS / MURS listening. Data, beacons and time signals "
        "are programmed but locked out of the scan. Press MEM scan and it "
        "sweeps every band."
    ),
    reserve_slots=40,
    blocks=(
        # -- one ascending run: 52 MHz -> 470 MHz, scanned end to end --------
        PlanBlock(
            label="Repeaters 6m 2m 70cm",
            selectors=(
                _near(
                    "PSHAM01",
                    dept=r"Analog 6 Meter|Analog 2 Meter|Analog 70 Centimeter|Linked Analog",
                ),
            ),
            tx_policy=TX_REPEATER,
            sort=SORT_FREQ,
            limit=420,
            notes=(
                "Every current WWARA analog machine within 75 miles. Transmit "
                "needs the published access tone, carried per channel where "
                "the coordinator publishes one. 1.25 m and 33/23 cm machines "
                "are dropped: this radio has no receiver there."
            ),
        ),
        PlanBlock(
            label="Simplex Calling",
            selectors=(
                _sel("HAM01", labels=r"simplex calling|SSB calling|SSB and CW calling"),
            ),
            tx_policy=TX_SIMPLEX,
            sort=SORT_FREQ,
            limit=10,
            notes="National calling frequencies on 6 m, 2 m and 70 cm (and 10 m SSB).",
        ),
        PlanBlock(
            label="HF Voice Nets",
            selectors=(
                _sel(
                    "HFNET01",
                    dept=r"Emergency and Weather|Centres of Activity|Traffic and Calling|Pacific Northwest",
                ),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=40,
            notes=(
                "Receive only. Emergency nets run to a protocol; traffic-net "
                "schedules in the notes are context, not fact."
            ),
        ),
        PlanBlock(
            label="HF Calling and QRP",
            selectors=(_sel("HAM01", labels=r"QRP|CALLING|CLLNG"),),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=40,
            notes=(
                "Band-plan phone/CW calling and QRP centres, 160 m through "
                "6 m. Receive only: transmit privileges vary by band and "
                "licence class, so enabling one is a deliberate per-channel "
                "choice."
            ),
        ),
        PlanBlock(
            label="Weather and Service Listening",
            selectors=(
                _sel("OZ01", dept="NOAA Weather"),
                _sel("FL75"),
                _sel("OZ01", dept=r"Marine and Vessel Traffic"),
                _sel("OZ01", dept=r"Aviation"),
                _sel("OZ01", dept=r"GMRS and FRS"),
                _sel("OZ01", dept=r"MURS"),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=110,
            notes=(
                "NWR, Puget Sound marine and vessel traffic, airband (AM), "
                "and GMRS/FRS/MURS. All receive only - the FTX-1 is not "
                "certified for Part 95 and does not transmit on marine or "
                "airband."
            ),
        ),
        # -- programmed, but locked out of the scan sweep -------------------
        PlanBlock(
            label="Data Beacons and Time",
            selectors=(
                _sel("HAM01", labels=r"FT8|FT4|WSPR|PSK31|RTTY|SSTV"),
                _sel(
                    "HFNET01",
                    dept=r"Propagation Beacons|Time and Frequency|Utility and Aeronautical|6 Meter Calling",
                ),
            ),
            tx_policy=TX_NONE,
            sort=SORT_FREQ,
            limit=120,
            skip_scan=True,
            notes=(
                "Digital watering holes, NCDXF/IARU beacons, WWV/WWVH and the "
                "always-on HF utility channels. Continuous carriers, so the "
                "scan sweep skips them; tune them by hand as propagation "
                "references."
            ),
        ),
    ),
)
