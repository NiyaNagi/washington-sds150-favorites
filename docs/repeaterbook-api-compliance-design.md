# RepeaterBook API Compliance Design

This document is the implementation and operating plan for using the
RepeaterBook API in Signal - KM7HKM Personal Radio Programmer. It is written
to answer RepeaterBook's review questions before the API adapter is enabled.

**Canonical public review URL:**
https://github.com/NiyaNagi/washington-sds150-favorites/blob/main/docs/repeaterbook-api-compliance-design.md

**[Data courtesy of RepeaterBook.com](https://www.repeaterbook.com/).**

## September 2026 Rejection Response

RepeaterBook's second admin note said the request was incomplete because the
public design URL and final controls were not supplied in the submitted review
packet. This revision responds to each item explicitly:

| Admin feedback | Final design response |
|---|---|
| No review URL supplied | The direct public design URL appears above and is the value in **Project Website or Review Link** below. |
| Visible attribution/link-back omitted | Every RepeaterBook-backed UI view and report displays **Data courtesy of RepeaterBook.com** linked to `https://www.repeaterbook.com/`; record details link to the relevant RepeaterBook detail page when available. |
| Geographic and result bounds omitted | Version 1 permits only Washington State (`country=United States`, `state_id=53`), requires one center point and a radius from 1 through 60 miles, filters locally by great-circle distance, and accepts no more than 250 candidates. |
| Numeric request/rate controls omitted | One HTTP request per manual refresh, no pagination, no parallel requests, no more than one refresh per 60 minutes and four per rolling 24 hours per user token. |
| HTTP 429 controls omitted | A 429 stops the refresh immediately. There is no same-action retry. The next attempt is blocked until the later of `Retry-After` or 60 minutes. |
| Cache TTL/retention/deletion omitted | Raw responses are fresh for 7 days and deleted by day 30; normalized/applied RepeaterBook records expire and are deleted by day 90 unless manually refreshed and reviewed again; an explicit delete action removes all RepeaterBook data immediately. |
| Local personal workflow required | The adapter runs only from an explicit local user action to program personally owned radios. There is no startup refresh, scheduler, server, proxy, public search, map, directory, feed, or API. |
| Per-user app-bound token required | Signal never accepts a shared `app_` token. Each user supplies only their own dashboard-issued `rbuapp_` token in the preferred `X-RB-App-Token` header. |

These are hard application limits, not estimates. If RepeaterBook imposes a
stricter approved scope or limit, the stricter value wins.

## Copy-Paste RepeaterBook Distributed-App Request
Select the **I develop or maintain a distributed app** access model. This is the
correct model because Signal is a locally run desktop application whose users
control their own configuration; it cannot safely embed or protect a shared
credential.

### Contact Name / Call Sign
```text
KM7HKM
```
### Contact Email
```text
<enter the email address associated with KM7HKM's RepeaterBook account>
```
### Project / Application Name
```text
Signal - KM7HKM Personal Radio Programmer
```
### Project Website or Review Link
```text
https://github.com/NiyaNagi/washington-sds150-favorites/blob/main/docs/repeaterbook-api-compliance-design.md
```
### Application User-Agent
```text
SignalWA/1.0 (+https://github.com/NiyaNagi/washington-sds150-favorites; <VALID_CONTACT_EMAIL>)
```
Replace `<VALID_CONTACT_EMAIL>` with the same reachable address entered in the
Contact Email field before submitting. The approved value, including that
address, will be used byte-for-byte in every request. Do not use a GitHub
no-reply address.

### Application Review Details
```text
Signal is a local, noncommercial, user-triggered personal radio programmer for KM7HKM's personally owned Kenwood TH-D75A, Uniden SDS150, TIDRADIO TD-H9, and Yaesu FTX-1. Public implementation design: https://github.com/NiyaNagi/washington-sds150-favorites/blob/main/docs/repeaterbook-api-compliance-design.md Version 1 is Washington-only: one manual request for country=United States and state_id=53, followed by local filtering around one user-selected center from 1 through 60 miles and target-radio bands; no more than 250 candidates may enter review. There is no pagination, parallelism, startup/scheduled refresh, server, proxy, public search, map, directory, feed, or secondary API. Each user supplies only their own dashboard-issued app-bound rbuapp_ token; Signal never accepts or embeds a shared app_ token. Hard client limits are one request per manual refresh, one refresh per 60 minutes, and four per rolling 24 hours. HTTP 429 stops immediately with no same-action retry; the next attempt is blocked until the later of Retry-After or 60 minutes. Raw cache is fresh for 7 days and deleted by day 30; derived records are deleted by day 90 unless manually refreshed and reviewed again; the user can immediately delete all RepeaterBook data. Every RepeaterBook-backed UI view and report visibly displays “Data courtesy of RepeaterBook.com” linked to https://www.repeaterbook.com/. Raw/cache data is never committed, published, sold, re-served, bulk-exported, or redistributed. The adapter remains disabled until these controls and tests are implemented and approval is granted.
```
### Primary RepeaterBook Use
Select: **Personal radio programming**
### Who Can Use It?
Select: **Private, single user**
### Estimated Users
```text
1
```
### API Workflow and Data Fields
```text
Version 1 is limited to Washington State. The user selects one center point, a whole-number radius from 1 through 60 miles, target-radio bands, and a target radio, then explicitly clicks Refresh RepeaterBook. Signal sends one Export API request with country=United States and state_id=53, performs no pagination, computes great-circle distance locally, rejects records without usable coordinates, excludes records outside the selected radius or target-radio bands/capabilities, and admits at most 250 candidates to the private review screen. If more than 250 match, nothing is imported and the user must reduce radius or bands. Fields used are repeater/state IDs, callsign, output/input frequency or offset, uplink/downlink tone or digital access value, operating mode, operational status, latitude/longitude, city, county, state, last update, and computed distance. Only user-selected records are normalized into the private programming catalog. Normal radio export never calls RepeaterBook. There is no general browser, map, directory, proxy, feed, bulk export, public API, or background synchronization.
```
### Relationship to RepeaterBook
```text
RepeaterBook is the source of current amateur-repeater listing data used for bounded local searches. Signal retains RepeaterBook source attribution and retrieval time with locally imported records. RepeaterBook is not affiliated with Signal, and Signal does not represent itself as endorsed by RepeaterBook.
```
### Credential Handling and Abuse Prevention
```text
Signal is a distributed local application. It will not request, embed, ship, or use a shared app_ token. Each approved user must generate and use their own app-bound rbuapp_ token from the RepeaterBook dashboard. In the current private single-user deployment, the only user is KM7HKM. The user's rbuapp_ token is loaded only at runtime from an environment variable or a local configuration file on a BitLocker-encrypted removable drive. It is never hard-coded, committed to Git, included in generated radio files, printed, or logged. Signal exposes no public web service, browser client, proxy, or API endpoint. If a token is lost, copied, or compromised, its owner will revoke or rotate it from the RepeaterBook dashboard.
```
### Rate and Abuse Controls
```text
Requests occur only after an explicit local user refresh. Signal sends the exact approved User-Agent and the user's own rbuapp_ token in X-RB-App-Token. Hard limits are one HTTP request per manual refresh, zero pagination requests, zero parallel requests, no more than one refresh per 60 minutes, and no more than four refreshes per rolling 24 hours per token. HTTP 429 stops immediately with no same-action retry; the next attempt is blocked until the later of Retry-After or 60 minutes. Authentication, scope, and User-Agent errors are never retried. There is no startup refresh, scheduler, crawl, burst, bypass, or request from normal radio generation. Any stricter RepeaterBook-approved limit overrides these local maxima.
```
### Cache and Retention Policy
```text
Raw API responses and normalized staging rows are stored only in the user's local SQLite application data outside the repository. Raw data is fresh for 7 days, may be viewed offline as visibly stale through day 30, and is automatically deleted no later than day 30. User-reviewed derived RepeaterBook records retain source ID, attribution, and retrieval date and are automatically deleted no later than day 90 unless the user manually refreshes and reviews them again. Purges run at startup and before and after every refresh. A Delete All RepeaterBook Data action immediately removes raw responses, staging rows, derived records, request history, and generated audit reports; token deletion is a separate explicit action. Cache and derived data are never committed, backed up by Signal, included in releases, published, sold, shared, re-served, or redistributed. Normal exports never refresh the cache.
```
### Attribution and Link-Back Plan
```text
Signal will visibly display “Data courtesy of RepeaterBook.com” and link that text to https://www.repeaterbook.com/ wherever RepeaterBook-derived records are shown: local dashboard search results, record details, CLI previews, Markdown/HTML review reports, and companion radio-export audit reports. Native radio file formats that cannot contain an attribution field will have the attribution in their companion export/audit report.
```
### Commercial Status
Select: **Non-commercial**
### Implementation Status
Select: **Planned**
### Source Availability
Select: **Open source**
```text
The source is publicly reviewable at: https://github.com/NiyaNagi/washington-sds150-favorites The RepeaterBook adapter is deliberately disabled while planned controls are implemented. The detailed compliance design, including token rules, numeric limits, cache duration, 429 handling, filtering, attribution, and non-redistribution controls, is publicly reviewable at: https://github.com/NiyaNagi/washington-sds150-favorites/blob/main/docs/repeaterbook-api-compliance-design.md
```
### Required Confirmations
Check all three confirmations:
- I will display “Data courtesy of RepeaterBook.com.” and link back to
  RepeaterBook where practical.
- I will not mirror, redistribute, bulk-export, re-serve, or use the data to
  build another directory, dataset, service, or API without written permission.
- I have read, understand, and agree to the API terms and site terms of service.
### Project Categories
Select: **Private/Internal**, **Open-Source**, **Hobby/Personal**

Current implementation status: the checked-in
`wasds150.sources.repeaterbook` adapter is intentionally unavailable and raises
`NotImplementedError`. No RepeaterBook token is present in this repository, no
RepeaterBook API calls are made by the current code, and no RepeaterBook data is
committed here. This document defines the rules the implementation must satisfy
before that adapter can be enabled.

## Project Identity

Application name:

Signal - KM7HKM Personal Radio Programmer

Repository:

https://github.com/NiyaNagi/washington-sds150-favorites

Application User-Agent:

```text
SignalWA/1.0 (+https://github.com/NiyaNagi/washington-sds150-favorites; <VALID_CONTACT_EMAIL>)
```

Before application submission, `<VALID_CONTACT_EMAIL>` will be replaced with
the reachable address in the request. Every RepeaterBook API request must send
the resulting approved `User-Agent` byte-for-byte. The adapter must reject
execution if it would otherwise use a default Python, requests, urllib, browser,
or HTTP-library user agent.

Operator:

KM7HKM, a newly licensed amateur radio operator using the application for their
own radios only.

## Purpose and Scope

Signal maintains a local, radio-neutral channel catalog and generates
programming files for personally owned radios. Current radios include:

- Kenwood TH-D75A
- Uniden SDS150
- TIDRADIO TD-H9
- Yaesu FTX-1

Version 1 will use RepeaterBook only to select currently listed Washington State
amateur repeaters for programming the operator's radios. The application needs
these fields when available:

- Repeater callsign
- Output frequency
- Input frequency or offset
- Access tone or digital access value
- Operating mode
- Status
- Latitude, longitude, city, county, and state
- Distance from the requested search center

The application is not a public API proxy, commercial product, directory mirror,
scraper, or bulk data collection project. It is a private, noncommercial,
single-user tool. Generated radio files are for programming personally owned
equipment only.

## Exact Workflow

RepeaterBook use will require an explicit manual refresh command or UI action.
Normal catalog generation will read from the local cache and will not contact
RepeaterBook.

Planned CLI shape:

```powershell
wasds150 sources configure --repeaterbook-token-env REPEATERBOOK_API_TOKEN
wasds150 sources fetch repeaterbook --state WA --center 47.633,-121.966 --radius-mi 60 --bands 2m,70cm --radio thd75
wasds150 sources update --only repeaterbook --preview
wasds150 sources update --only repeaterbook --apply
wasds150 plan export thd75-ames-lake --target thd75-file --out radio-configs
```

Planned UI shape:

1. The operator opens the local dashboard on their own Windows machine.
2. The operator chooses a saved location profile or enters a travel location.
3. The operator chooses bands and a maximum radius.
4. The operator clicks an explicit `Refresh RepeaterBook` action.
5. The application fetches bounded pages with conservative spacing.
6. The application normalizes records into an internal review table.
7. The operator reviews additions and changes before applying them.
8. Radio export uses the reviewed local catalog, not a live API call.

No scheduled job, background crawler, or automatic startup refresh will call
RepeaterBook.

### Planned implementation locations

- `src/wasds150/sources/repeaterbook.py`: validate the Washington-only request,
  attach the approved headers, issue exactly one request, validate response
  shape, calculate distance, enforce the 250-candidate fail-closed cap, and
  normalize only reviewed fields.
- `src/wasds150/sources/config.py`: store only the environment-variable name or
  external credential-file path; reject `app_` tokens and accept only
  `rbuapp_` tokens.
- `src/wasds150/cache/http.py` and `src/wasds150/cache/store.py`: enforce the
  7-day freshness TTL, day-30 raw deletion, day-90 derived deletion, request
  ledger, and immediate purge operation.
- `src/wasds150/cli.py` and the local web UI: expose only explicit refresh,
  preview, apply, status, and delete actions; display attribution and source
  links anywhere RepeaterBook data appears.
- `src/wasds150/export/report.py`: put linked attribution in companion HTML or
  Markdown audit output whenever selected radio channels came from RepeaterBook.
- `tests/test_repeaterbook_source.py`: use synthetic responses to prove token
  rejection/redaction, exact headers, one-request behavior, geographic and
  result caps, no pagination/parallelism, 429 lockout, expiry/deletion, output
  filtering, and attribution. Tests will never contain a live token or copied
  RepeaterBook response.

## Token Handling

Signal is a distributed application and will never use a shared `app_` token.
Every user must generate and use their own RepeaterBook dashboard-issued,
app-bound `rbuapp_` token. In the present private deployment, the only user is
KM7HKM.

The token will be provided at runtime from one of these locations only:

- `REPEATERBOOK_API_TOKEN` environment variable containing that user's
  `rbuapp_` token
- A local config file on a BitLocker-encrypted removable thumb drive under the
  operator's control

The token must never be:

- Hard-coded in source code
- Committed to Git
- Included in generated radio files
- Printed in reports
- Written to logs
- Exposed through a website, browser client, API endpoint, shared service, or
  public build artifact

The adapter validates the `rbuapp_` prefix before network access and sends the
token only as `X-RB-App-Token`. A value beginning with `app_` is rejected as an
invalid credential for this distributed application.

The local config file path must stay outside the repository. If a path is stored
in project configuration, only the path is stored, not the token value. The
adapter will redact the token from exceptions and structured logs using the
project logging redaction path.

If the removable drive is lost, copied, or suspected to be compromised, the
credential will be revoked or rotated immediately. Backups containing local
configuration remain encrypted and are never stored in this source repository.

## Request Limits

The adapter will enforce local numeric limits even if the API would allow more.

Hard limits:

- Exactly one RepeaterBook HTTP request per successful manual refresh.
- No more than one manual refresh per 60 minutes per user token.
- No more than four manual refreshes per rolling 24 hours per user token.
- Maximum 250 candidate records admitted to review; if 251 or more match, the
  import fails closed and asks the user to reduce radius or bands.
- No parallel RepeaterBook requests.
- No pagination requests.
- No multi-state, national, or all-state crawl loop.
- No refresh on application startup.

Allowed query bounds:

- Version 1 sends only `country=United States` and `state_id=53` (Washington).
- Every refresh requires exactly one geographic center.
- Radius must be a whole number from 1 through 60 miles; default is 60 miles.
- At least one target-radio-supported amateur band must be selected.
- Great-circle distance and band/radio-capability filtering happen locally
  before a record can enter review.
- Records without usable coordinates are rejected.

Pagination rules:

- Version 1 does not paginate.
- If RepeaterBook later requires pagination, the adapter remains disabled until
  a revised, approved policy and tested numeric page cap are documented.

The first implementation must include tests that prove the rate limiter,
geographic/result bounds, one-request behavior, and no-pagination rule without
requiring live API access.

## HTTP Error and 429 Handling

The adapter will use conservative backoff and will fail closed.

Rules:

- `200`: validate schema, normalize supported records, and cache the raw
  response locally.
- `304`: use the existing local cached body when conditional requests are
  supported.
- `400` or `404`: stop the current query and report the bad filter or endpoint.
- `401` or `403`: stop all RepeaterBook requests, redact the token from the
  error, and require operator action.
- `408`, `425`, `429`, `500`, `502`, `503`, `504`: stop the refresh without an
  automatic same-action retry.

Backoff rules:

- On `429`, stop immediately and make no retry in the same user action.
- Honor `Retry-After` when present.
- If `Retry-After` is absent, block the next refresh for 60 minutes.
- If `Retry-After` is shorter than 60 minutes, the 60-minute local interval
  still applies; if longer, the server value applies.
- Authentication, scope, and User-Agent errors require correction and are never
  retried automatically.

## Filtering and Radio Compatibility

Fetched RepeaterBook records will not be copied directly into radio files.
They will first be normalized into the project catalog and filtered by radio
capability.

Filtering rules:

- Include only amateur repeaters relevant to the requested geography and band.
- Preserve source identity and retrieval time on each imported fact.
- Drop or mark unsupported modes for a specific radio rather than coercing them.
- Mark non-amateur services receive-only if they ever appear in an adjacent
  local planning context.
- Do not synthesize missing tones, offsets, coordinates, or callsigns.
- Do not export disabled, stale, unknown-status, or unsupported entries without
  explicit operator review.

Generated radio behavior:

- Generated files may contain the selected frequency, offset, tone, mode, name,
  and location fields required to program the operator's own radios.
- Generated files must not include the raw RepeaterBook response body.
- Generated files must not include the API token.
- Generated files must not be used as a public RepeaterBook data export.
- Radio-specific exports will continue to show drop/warning reports for records
  the radio cannot represent.

## Cache Duration and Retention

RepeaterBook responses will be cached locally to avoid repeated API calls during
normal radio-file generation.

Cache storage:

- SQLite-backed HTTP cache under the user's local `wasds150` configuration home.
- Not stored in the repository.
- Not copied into release archives.
- Not included in generated radio programming files.

Freshness rules:

- Fresh cache TTL: 7 days.
- Stale raw data may be viewed offline, visibly marked stale, only through day
  30; it cannot be newly applied after the 7-day freshness TTL.
- Raw responses and normalized staging rows are deleted no later than day 30.
- Derived reviewed records are deleted no later than day 90 unless manually
  refreshed and reviewed again; they retain source ID, attribution, and
  retrieval date while present.

Operational rules:

- A normal export uses cached/reviewed local records only.
- A refresh requires explicit operator action.
- Offline mode never calls RepeaterBook.
- Purges run at startup and before and after every refresh.
- `Delete All RepeaterBook Data` immediately deletes raw responses, staging
  rows, derived records, request history, and generated audit reports.
- Deleting the locally stored token is a separate explicit action.
- The local status command will show last refresh time and whether cached data
  is fresh, stale, or expired.

## Visible Attribution and Link-Back

Any user-visible screen, report, preview, or generated documentation that shows
RepeaterBook-derived repeater records must display this attribution text:

```text
Data courtesy of RepeaterBook.com
```

The text must link to:

```text
https://www.repeaterbook.com/
```

Attribution placement:

- Local dashboard repeater search results: visible above or below the result
  table.
- Local dashboard record detail view: visible near the source/provenance block.
- CLI preview/report output: visible once per RepeaterBook-backed report.
- Markdown/HTML review reports: visible in the source/provenance section.
- Generated radio programming audit reports: visible when any exported channel
  came from RepeaterBook.

When a stable RepeaterBook record ID permits a detail URL, the record view links
to that relevant RepeaterBook page. Other online attribution links to
`https://www.repeaterbook.com/`.

Attribution is not required inside binary/native radio programming files when
the radio format has no suitable attribution field. In that case, the companion
export/audit report must include the visible attribution and link.

## Non-Redistribution Commitments

This project will not redistribute RepeaterBook data.

Specifically:

- Raw API responses will not be committed to the repository.
- Cache files will not be committed to the repository.
- Bulk exports, mirrors, or database snapshots will not be published.
- RepeaterBook-derived local catalog caches will not be sold, sublicensed, or
  made available as a public download.
- The application will not expose RepeaterBook data through a public website,
  public API, hosted proxy, or shared service.
- Generated radio files are for programming personally owned equipment only.

Repository rules:

- `.gitignore` must exclude local source caches, credential files, and generated
  private radio artifacts.
- Tests must use synthetic fixtures or tiny redacted examples, not copied live
  RepeaterBook API responses.
- Documentation may describe RepeaterBook field names and usage patterns, but
  must not embed copied bulk data.

## Implementation Acceptance Criteria

The RepeaterBook adapter must not be enabled until all of these are true:

1. Every live request sends the exact approved `SignalWA/1.0` User-Agent with
  public project URL and reachable contact email.
2. Token loading supports only a user-owned `rbuapp_` token from an environment
  variable or external encrypted-drive config, with no shared `app_` token and
  no repo-stored token path required.
3. Token redaction is covered by tests.
4. No live request can run without an explicit manual refresh action.
5. No parallel RepeaterBook requests are possible.
6. Exactly one request per refresh, one refresh per 60 minutes, and four per
   rolling 24 hours are enforced per token.
7. Version 1 accepts only Washington (`state_id=53`), one center, radius 1-60
   miles, and at least one target-radio-supported band.
8. At most 250 candidates enter review; 251 or more fails closed.
9. Version 1 sends no pagination or parallel requests.
10. `429` stops immediately with no same-action retry and locks refresh until
  the later of `Retry-After` or 60 minutes.
11. Raw data is fresh for 7 days and deleted by day 30; derived records are
  deleted by day 90 unless manually refreshed and reviewed again; immediate
  deletion is available and tested.
12. Generated radio files contain only selected programming fields and never raw
    API bodies or credentials.
13. Any user-visible RepeaterBook-derived report or UI includes visible
    `Data courtesy of RepeaterBook.com` attribution linking to
    `https://www.repeaterbook.com/`.
14. Documentation and tests confirm raw RepeaterBook data is not committed,
    republished, sold, or redistributed.

## Copy-Ready Reapplication Summary

Signal is a private, noncommercial, single-user personal radio programmer for
KM7HKM. Version 1 queries RepeaterBook only after an explicit manual refresh for
Washington State (`state_id=53`), then locally filters around one center by a
1-60 mile radius, selected bands, and radio capability. At most 250 candidates
may enter review. It will use the exact approved `SignalWA/1.0` User-Agent with
the public project URL and reachable contact email on every request.

Signal will never use a shared `app_` token. Each user supplies their own
RepeaterBook dashboard-issued, app-bound `rbuapp_` token at runtime through
`REPEATERBOOK_API_TOKEN` or a local config file on a BitLocker-encrypted
removable drive. It will never be hard-coded, committed, logged, included in
generated radio files, or exposed through a website/API/proxy/shared service.

The implementation makes exactly one request per manual refresh, no pagination
or parallel requests, no more than one refresh per 60 minutes, and no more than
four refreshes per rolling 24 hours per token. HTTP 429 stops immediately with
no same-action retry; the next refresh is blocked until the later of
`Retry-After` or 60 minutes.

Responses are cached locally only under the user's config home. Raw data is
fresh for 7 days and deleted by day 30. Derived records are deleted by day 90
unless manually refreshed and reviewed again. An explicit delete action removes
all RepeaterBook data immediately. Normal radio exports use only reviewed local
records and do not call the API. Raw RepeaterBook data, cache files, tokens, and
database snapshots will not be committed, published, sold, or redistributed.

Every UI screen, CLI report, Markdown/HTML report, or generated audit report
that displays RepeaterBook-derived records will visibly show
`Data courtesy of RepeaterBook.com` with a link to
`https://www.repeaterbook.com/`. Native radio files that cannot carry
attribution will have a companion export/audit report containing the visible
attribution.