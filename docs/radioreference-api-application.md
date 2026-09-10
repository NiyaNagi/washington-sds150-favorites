# RadioReference API key application

Text to paste into <https://www.radioreference.com/account/api/apply>. The
form's fields are reproduced in order. Replace `<email>` before submitting.

## Application Name

```
Signal - WA7DAM Personal Radio Programmer
```

## Short Description

```
Single-user Python command-line tool that builds programming files for my own scanners and amateur transceivers from RadioReference county data.
```

## Detailed Use Case

```
What it does. Signal is an open-source (MIT) Python 3 command-line program I wrote and run on my own Windows PC to program the radios I own: a Uniden SDS150 scanner, an Anytone AT-D890UV DMR/NXDN handheld, a Kenwood TH-D75A, a Yaesu FTX-1 and a TIDRADIO TD-H9. It keeps one local, radio-neutral channel catalog for Washington State and turns it into each radio's native programming file (Sentinel .hpe, Anytone CPS CSV bundle, Kenwood MCP-D75 image, RT Systems file, CHIRP CSV). Source: https://github.com/NiyaNagi/washington-sds150-favorites.

Who uses it. Only me, WA7DAM, a General-class amateur radio operator in King County, Washington, holding an active RadioReference Premium subscription. The application is private and non-commercial; it has no other users, no hosted component, no public search, map, directory, feed or API.

How RadioReference data is used. Today I download county and state CSV exports by hand from my Premium account and import them locally. The API would replace that manual step with a refresh command I run myself, on demand, roughly monthly. Operations I intend to call, in this order: getStateInfo (stid 53) to list counties; getCountyInfo for the counties within about 60 miles of home (King, Snohomish, Pierce, Kitsap, Island, Skagit, Thurston, Mason, Jefferson, Kittitas, Chelan); getSubcatFreqs and getAgencyInfo for each category the county returns; getCountyFreqsByTag for the statewide categories; getTrsDetails, getTrsSites, getTrsTalkgroupCats and getTrsTalkgroups for the trunked systems those counties list (PSERN, Sno911, SS911 and similar) so the SDS150 favorites lists carry current talkgroups; getTag and getMode once per refresh for the code tables; occasionally fccGetProxCallsigns to confirm a licensee near a frequency I am curating.

Call volume and caching. One manual refresh is on the order of 300 to 500 calls (roughly 11 counties times their subcategories and systems). Responses are cached locally for seven days and a refresh within that window re-uses the cache instead of calling again. Calls are serialized with a delay between them; there is no scheduler, background job, crawler or parallel fetching.

Data handling and presentation. Everything fetched is stored only in my local configuration directory on my own machine, marked as licensed in the catalog, and excluded from the public repository, from generated files I commit, and from any shareable bundle. Data is presented to me alone, as a terminal report and in a local web page served on 127.0.0.1, and written into programming files loaded into my own radios. Nothing is redistributed, re-served, scraped from the website, or combined with Broadcastify; the application does not use Broadcastify APIs, feeds or audio in any way.

Attribution. Every imported channel keeps its RadioReference source URL in its notes and the generated reports name RadioReference as the source.
```

## Distribution

```
Private / Internal - the application is for personal use, internal company use, or a closed group.
```

## Platform

```
Windows (desktop command-line application, Python 3.9+)
```

## Checkboxes

- [x] I have read the Database Web Service API knowledge base article.
- [x] I understand this Application API Key is for the RadioReference
      Database only and is not for anything related to Broadcastify.

## Contact

```
<email>
```

## After approval

```powershell
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources configure --rr-username <username> --rr-app-key <key>
$env:WASDS150_RR_PASSWORD = '<password>'     # never written to disk
.\.venv\Scripts\wasds150.exe --home .wasds150-home sources fetch radioreference_api
```

The live adapter (`src/wasds150/sources/radioreference_api.py`) is the
follow-up once the key arrives; until then the county/state CSV export path
(`sources configure --rr-export-path .wasds150-home\rr-exports`) does the same
job by hand.
