# RepeaterBook API Compliance Design

This document is the implementation and operating plan for using the
RepeaterBook API in Signal - KM7HKM Personal Radio Programmer. It is written
to answer RepeaterBook's review questions before the API adapter is enabled.

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
https://github.com/NiyaNagi/washington-sds150-favorites
```
### Application User-Agent
```text
SignalWA/1.0 (KM7HKM personal radio programmer)
```
### Application Review Details
```text
Signal is a private, noncommercial, single-user personal radio programming
application maintained by KM7HKM. It runs locally on the operator's Windows PC
and creates programming files only for the operator's personally owned radios:
Kenwood TH-D75A, Uniden SDS150, TIDRADIO TD-H9, and Yaesu FTX-1.

The RepeaterBook integration is planned but is not yet enabled. The repository
contains a public, detailed pre-implementation compliance design and the source
adapter remains disabled until these controls are implemented and tested:
https://github.com/NiyaNagi/washington-sds150-favorites/blob/main/docs/repeaterbook-api-compliance-design.md

Signal is not a public API proxy, directory, map, data mirror, bulk downloader,
or secondary service. It will not publish, commit, sell, or redistribute raw
RepeaterBook data. A manual refresh uses a bounded nearby-repeater query, saves
the response only in the local private cache, presents proposed changes for
review, and creates radio files only after approval. Normal radio-file export
reads the reviewed local cache and never makes a RepeaterBook request.
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
An explicit manual refresh searches only for amateur repeaters relevant to the
radio being configured. Each request is bounded by state and/or a user-selected
travel or home location, radius, and band. The default search is Washington
State within 60 miles; the maximum radius is 150 miles. The user reviews the
locally cached results before selected records are written to a personal radio
programming file.

Fields used when available are: repeater callsign, output frequency, input
frequency or offset, access tone/digital access value, operating mode, status,
latitude, longitude, city, county, state, and distance from the requested search
center. Signal filters each record for the target radio's capability; it does
not invent missing frequency, tone, offset, location, callsign, or mode values.

This is not a proxy, mirror, directory, map, bulk download, secondary API, or
background synchronization service. Normal exports use only locally reviewed
cached records and do not call the API.
```
### Relationship to RepeaterBook
```text
RepeaterBook is the source of current amateur-repeater listing data used for
bounded local searches. Signal retains RepeaterBook source attribution and
retrieval time with locally imported records. RepeaterBook is not affiliated
with Signal, and Signal does not represent itself as endorsed by RepeaterBook.
```
### Credential Handling and Abuse Prevention
```text
Signal is a distributed local application. It will not request, embed, ship,
or use a shared app_ token. Each approved user must generate and use their own
app-bound rbuapp_ token from the RepeaterBook dashboard. In the current private
single-user deployment, the only user is KM7HKM.

The user's rbuapp_ token is loaded only at runtime from an environment variable
or a local configuration file on a BitLocker-encrypted removable drive. It is
never hard-coded, committed to Git, included in generated radio files, printed,
or logged. Signal exposes no public web service, browser client, proxy, or API
endpoint. If a token is lost, copied, or compromised, its owner will revoke or
rotate it from the RepeaterBook dashboard.
```
### Rate and Abuse Controls
```text
RepeaterBook requests occur only after an explicit manual refresh; never at
startup, on a schedule, or from normal radio-file generation. Signal sends the
exact User-Agent: SignalWA/1.0 (KM7HKM personal radio programmer).

It permits no parallel requests, at most one request every 3 seconds, at most
20 requests per manual refresh, and at most 200 requests per rolling 24-hour
local window. Each query is bounded by state, geography/radius, and/or band;
there is no national or all-state crawl. Pagination stops at the API's final
page, an empty result, 10 pages, 2,000 accepted records, or the request cap.

For HTTP 429, Signal honors Retry-After. If it is absent, it retries at most
three times with waits of 30 seconds, 2 minutes, and 10 minutes, then stops the
refresh. It also stops on unrecoverable authentication/authorization errors and
never tries parallel or bypass requests.
```
### Cache and Retention Policy
```text
Raw API responses are cached only in the user's local SQLite-backed application
cache, outside the repository. Freshness TTL is 7 days. Offline use of a stale
response is allowed for up to 30 days. Raw response bodies are automatically
purged after 90 days. Locally reviewed derived programming entries may remain
in the private catalog until the user removes them, with RepeaterBook attribution
and retrieval date retained.

Cache files are not committed, included in release archives, included in
generated radio files, published, sold, or shared. Normal exports use this
reviewed local cache and never trigger a refresh.
```
### Attribution and Link-Back Plan
```text
Signal will visibly display “Data courtesy of RepeaterBook.com” and link that
text to https://www.repeaterbook.com/ wherever RepeaterBook-derived records are
shown: local dashboard search results, record details, CLI previews, Markdown/
HTML review reports, and companion radio-export audit reports. Native radio
file formats that cannot contain an attribution field will have the attribution
in their companion export/audit report.
```
### Commercial Status
Select: **Non-commercial**
### Implementation Status
Select: **Planned**
### Source Availability
Select: **Open source**
```text
The source is publicly reviewable at:
https://github.com/NiyaNagi/washington-sds150-favorites

The RepeaterBook adapter is deliberately disabled while planned controls are
implemented. The detailed compliance design, including token rules, numeric
limits, cache duration, 429 handling, filtering, attribution, and
non-redistribution controls, is publicly reviewable at:
https://github.com/NiyaNagi/washington-sds150-favorites/blob/main/docs/repeaterbook-api-compliance-design.md
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
SignalWA/1.0 (KM7HKM personal radio programmer)
```

Every RepeaterBook API request must send that exact `User-Agent`. The adapter
must reject execution if it would otherwise fall back to the default Python,
requests, urllib, browser, or HTTP-library user agent.

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

RepeaterBook will be used only to find currently listed amateur repeaters near
the operator's home and travel destinations, primarily in Washington State. The
application needs these fields when available:

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
wasds150 sources fetch repeaterbook --state WA --center 47.633,-121.966 --radius-mi 60 --bands 2m,70cm
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

The local config file path must stay outside the repository. If a path is stored
in project configuration, only the path is stored, not the token value. The
adapter will redact the token from exceptions and structured logs using the
project logging redaction path.

If the removable drive is lost, copied, or suspected to be compromised, the
credential will be revoked or rotated immediately. Backups containing local
configuration remain encrypted and are never stored in this source repository.

## Request Limits

The adapter will enforce local numeric limits even if the API would allow more.

Default limits:

- Maximum one RepeaterBook request every 3 seconds.
- Maximum 20 RepeaterBook requests per manual refresh operation.
- Maximum 200 RepeaterBook requests per rolling 24-hour local window.
- Maximum 2,000 accepted repeater records per manual refresh operation.
- No parallel RepeaterBook requests.
- No national or all-state crawl loop.
- No refresh on application startup.

Allowed query bounds:

- A query must be bounded by state, geographic center plus radius, band, or an
  equivalent API-supported narrow filter.
- Default radius is 60 miles.
- Maximum radius is 150 miles per manual refresh.
- Default state is `WA` when a state is needed.
- The operator may request travel destinations manually, but each destination is
  an explicit bounded query.

Pagination rules:

- Page size must use the RepeaterBook API default unless the API documentation
  recommends a smaller value.
- Maximum pages per query: 10.
- Maximum records consumed per page: 200.
- Stop immediately when the API reports the final page, returns no records, or
  reaches the local page or record limit.
- Persist the last request timestamp before the next page is requested.

The first implementation must include tests that prove the rate limiter,
pagination stop conditions, and max-request cap are enforced without requiring
live API access.

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
- `408`, `425`, `429`, `500`, `502`, `503`, `504`: retry only within the limits
  below.

Backoff rules:

- Honor `Retry-After` if RepeaterBook returns it.
- If no `Retry-After` is present, use exponential backoff of 30 seconds,
  2 minutes, then 10 minutes.
- Maximum retries per request: 3.
- Maximum retry wait budget per manual refresh: 15 minutes.
- On `429`, stop all pagination for that refresh after the final retry fails.
- Never open additional parallel requests while waiting.

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
- Stale-but-usable offline window: 30 days.
- Hard retention limit for raw RepeaterBook API response bodies: 90 days.
- Derived reviewed catalog entries may remain in the operator's local private
  catalog until manually removed, but retain RepeaterBook attribution and
  retrieval date.

Operational rules:

- A normal export uses cached/reviewed local records only.
- A refresh requires explicit operator action.
- Offline mode never calls RepeaterBook.
- Cached raw responses older than 90 days are purged before or after refresh.
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

1. Every live request sends `User-Agent: SignalWA/1.0 (KM7HKM personal radio programmer)`.
2. Token loading supports only a user-owned `rbuapp_` token from an environment
  variable or external encrypted-drive config, with no shared `app_` token and
  no repo-stored token path required.
3. Token redaction is covered by tests.
4. No live request can run without an explicit manual refresh action.
5. No parallel RepeaterBook requests are possible.
6. Rate limit of at most one request per 3 seconds is enforced.
7. Per-refresh cap of 20 requests is enforced.
8. Rolling 24-hour cap of 200 requests is enforced.
9. Pagination stops at 10 pages, 2,000 accepted records, final page, or empty
   response.
10. `429` handling honors `Retry-After` and otherwise uses bounded exponential
    backoff.
11. Fresh cache TTL is 7 days, stale offline window is 30 days, and raw response
    retention is no more than 90 days.
12. Generated radio files contain only selected programming fields and never raw
    API bodies or credentials.
13. Any user-visible RepeaterBook-derived report or UI includes visible
    `Data courtesy of RepeaterBook.com` attribution linking to
    `https://www.repeaterbook.com/`.
14. Documentation and tests confirm raw RepeaterBook data is not committed,
    republished, sold, or redistributed.

## Copy-Ready Reapplication Summary

Signal is a private, noncommercial, single-user personal radio programmer for
KM7HKM. It will query RepeaterBook only after an explicit manual refresh for a
bounded state/radius/band/radio-capability workflow, primarily Washington State
and travel destinations. It will use the exact user agent
`SignalWA/1.0 (KM7HKM personal radio programmer)` on every API request.

Signal will never use a shared `app_` token. Each user supplies their own
RepeaterBook dashboard-issued, app-bound `rbuapp_` token at runtime through
`REPEATERBOOK_API_TOKEN` or a local config file on a BitLocker-encrypted
removable drive. It will never be hard-coded, committed, logged, included in
generated radio files, or exposed through a website/API/proxy/shared service.

The implementation will make no parallel RepeaterBook requests. It will enforce
one request every 3 seconds, no more than 20 requests per manual refresh, no
more than 200 requests per rolling 24 hours, no more than 10 pages per query,
and no more than 2,000 accepted records per refresh. On HTTP 429 it will honor
`Retry-After` or back off for 30 seconds, 2 minutes, then 10 minutes, with at
most 3 retries and a 15-minute retry budget.

Responses will be cached locally only under the user's config home. Fresh cache
TTL is 7 days, stale offline use is allowed for 30 days, and raw response bodies
are purged after 90 days. Normal radio exports use the reviewed local cache and
do not call the API. Raw RepeaterBook data, cache files, tokens, and database
snapshots will not be committed, published, sold, or redistributed.

Every UI screen, CLI report, Markdown/HTML report, or generated audit report
that displays RepeaterBook-derived records will visibly show
`Data courtesy of RepeaterBook.com` with a link to
`https://www.repeaterbook.com/`. Native radio files that cannot carry
attribution will have a companion export/audit report containing the visible
attribution.