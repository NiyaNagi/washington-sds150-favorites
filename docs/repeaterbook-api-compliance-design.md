# RepeaterBook API Compliance Design

This document is the implementation and operating plan for using the
RepeaterBook Export API in Signal - WA7DAM Personal Radio Programmer. It is
written for RepeaterBook's review of the application, and it describes code
that now exists in this repository: implemented, tested, and **off by default
until RepeaterBook approves it**.

**Canonical public review URL:**
https://github.com/NiyaNagi/washington-sds150-favorites/blob/main/docs/repeaterbook-api-compliance-design.md

**[Data courtesy of RepeaterBook.com](https://www.repeaterbook.com/).**

## Changes since request #229

| Item | At request #229 | Now |
|---|---|---|
| User-Agent | The design showed a placeholder contact, and the submitted value did not match the design's final form. | One constant, sent byte-for-byte, carrying the public project URL and a reachable contact: `SignalWA/1.0 (+https://github.com/NiyaNagi/washington-sds150-favorites; ajamess@gmail.com)`. Anything else is refused before a request is built. |
| Implementation and tests | The adapter raised `NotImplementedError`. | Implemented and tested in public: <COMMIT_URL>. Still unable to send a request without a local enable flag (off by default) and the user's own `rbuapp_` token. |
| Repository name | `NiyaNagi/washington-sds150-favorites` | Unchanged. A rename to match the application name was offered; it has not been made, so every URL in this document and in the User-Agent resolves as written. |
| Geographic scope | Washington only, one request per refresh. | An allowlist of regions (Washington, Oregon, Idaho enabled; British Columbia listed but disabled), with a per-token budget counted in HTTP requests. **Proposed; needs RepeaterBook's approval.** See [Regions and request limits](#regions-and-request-limits-proposed). |
| Use cases | Programming radios for the home area. | Also travel, and pulling repeaters from surrounding regions such as Oregon and British Columbia. See [Use cases](#use-cases). |
| Endpoint and token scopes | Requested `api.export` and `api.export_row`. | Only `api.export` is needed. The documentation's example `export.php?country=United%20States&country=Canada` shows the North America endpoint serves Canada too, so the rest-of-world endpoint is never called and `api.export_row` is withdrawn. The province identifier is an open question (below). |
| RepeaterBook-derived data in the repository | Seven Clallam County repeaters and a statewide sample row cited RepeaterBook listing pages as their source, contradicting this document. | Removed. Each value was re-sourced from the WWARA coordination database or deleted. `tests/test_no_repeaterbook_data.py` now fails if any committed catalog row, channel or radio file cites a RepeaterBook repeater data page. The removed rows remain in git history. |

These are hard application limits, not estimates. If RepeaterBook approves a
stricter scope or limit, the stricter value wins: every number lives in one
module, `src/wasds150/sources/repeaterbook/policy.py`.

## Current implementation status

Implemented, and disabled pending RepeaterBook approval. A live request needs
all three of:

1. the local enable flag, which defaults **off** and says "pending
   RepeaterBook approval" until the operator turns it on;
2. the operator's own app-bound `rbuapp_` token, from an environment variable
   or an external file; and
3. an explicit refresh command or UI action.

No token is present in this repository. The code has never made a live
request: every test uses synthetic records and a fake transport, and the test
suite replaces the real transport with one that fails the test if it is
called. No RepeaterBook data is committed here.

## Project identity

| | |
|---|---|
| Application name | Signal - WA7DAM Personal Radio Programmer |
| Repository | https://github.com/NiyaNagi/washington-sds150-favorites |
| User-Agent | `SignalWA/1.0 (+https://github.com/NiyaNagi/washington-sds150-favorites; ajamess@gmail.com)` |
| Contact | ajamess@gmail.com |
| Operator | WA7DAM, a General-class amateur radio operator, programming their own radios only |
| API documentation followed | https://www.repeaterbook.com/wiki/doku.php?id=api |

## Purpose and scope

Signal maintains a local, radio-neutral channel catalog and generates
programming files for personally owned radios:

- Kenwood TH-D75A
- Uniden SDS150
- TIDRADIO TD-H9
- Yaesu FTX-1
- Anytone AT-D890UV

RepeaterBook is used only to select currently listed amateur repeaters near a
chosen point so the operator can program their own radios. The fields used,
when present, are: repeater id, callsign, output and input frequency, uplink
and downlink tone, analog capability, operational status, use (open/closed),
nearest city, county, state, country, and coordinates.

The application is not a public API proxy, commercial product, directory
mirror, scraper, map, or nearby-repeater finder. It is a private,
noncommercial, single-user programming tool. Generated radio files are for the
operator's own equipment.

### Use cases

- **Home area.** Washington, one centre, up to 60 miles.
- **Travel.** Before a trip, one refresh for the destination: for example
  Oregon, centred on Bend, 60 miles, 2 m and 70 cm, for the TH-D75.
- **Border and surrounding regions.** Up to three regions in one action when
  the area of interest straddles a line: for example Washington, Oregon and
  Idaho around the Tri-Cities, or Washington and British Columbia near Blaine
  once the province parameter is confirmed.

In every case the result is filtered locally to one centre and radius, and
reviewed before anything reaches a radio.

## Exact workflow

Normal catalog generation and radio export read only local data and never
contact RepeaterBook. RepeaterBook is never run by `sources update` or
`sources fetch`, which refuse it by name and skip it when updating
everything. It has its own commands:

```powershell
wasds150 repeaterbook configure --token-env REPEATERBOOK_API_TOKEN   # stores the NAME only
wasds150 repeaterbook configure --enable                             # only after approval
wasds150 repeaterbook refresh --regions WA --center 47.633,-121.966 --radius-mi 60 --bands 2m,70cm --radio th-d75
wasds150 repeaterbook review --report md
wasds150 repeaterbook apply
wasds150 plan export thd75-ames-lake --target thd75-file --with-repeaterbook
```

Also: `status` (flag, token source and fingerprint, budget, lockouts, cache
freshness), `regions`, `records`, `purge`, `unblock` (after an authentication
error has been corrected), `forget-token`, and `delete-all --yes`.

The local web UI's Advanced tab has a **RepeaterBook (disabled until
approved)** panel. It shows the adapter's state and greys out **Refresh
RepeaterBook** until the enable flag and a token are both set. The operator
picks up to three regions, one centre, a radius, bands and a radio, reviews
the staged candidates (with attribution above the table and a link per
record), and applies them. The browser never sees or sends the token.

1. The operator starts a refresh by hand.
2. The request is checked against every bound below. If any fails, nothing is
   sent.
3. One HTTP request per region, in sequence.
4. Records are filtered locally and staged for review.
5. The operator reviews the candidates and applies them.
6. `plan export ... --with-repeaterbook` adds the applied records as a final
   block, reading the local store only.

There is no scheduler, background refresh, or refresh at startup. The
application's global offline mode (`sources configure --offline`) also refuses
a live refresh.

### Implementation

| Module | Role |
|---|---|
| `sources/repeaterbook/policy.py` | Every limit and identifier, and the region allowlist |
| `sources/repeaterbook/token.py` | Token loading, prefix rules, fingerprint, redaction registration |
| `sources/repeaterbook/client.py` | The only code that sends a request: exact User-Agent, token header, no redirects, no retry, size limit, error classification |
| `sources/repeaterbook/store.py` | A dedicated store with retention and Delete All |
| `sources/repeaterbook/normalize.py` | Response parsing and local filtering |
| `sources/repeaterbook/service.py` | Refresh, review, apply, status; every guard in one place |
| `sources/repeaterbook/catalog.py` | Applied records as a local-only list for plan export |
| `cli_repeaterbook.py`, `webui/repeaterbook_api.py` | The CLI commands and UI routes, both calling the service |
| `tests/test_repeaterbook.py` | The acceptance tests (mapped below) |

## Token handling

Signal is a distributed application and never uses a shared `app_` token.
Each user generates their own app-bound `rbuapp_` token for this application
on RepeaterBook's API Apps page. In the present private deployment the only
user is WA7DAM.

- The token is read at run time from the `REPEATERBOOK_API_TOKEN` environment
  variable (or another variable the operator names), or from a file that must
  be an absolute path **outside** this repository, for example on a
  BitLocker-encrypted drive. A file path inside the repository is refused.
- Local configuration stores only the variable's name or the file's path,
  never the token. Configuration refuses a value that looks like a token where
  a name belongs, and the UI refuses a `token` field outright.
- The token must start with `rbuapp_`. A value starting with `app_` is refused
  as a credential this application never accepts. Error messages never quote
  the value.
- It is sent only in the `X-RB-App-Token` header. It never appears in a URL
  (checked on every request), cache key, database row, raw-response file,
  log, exception, report, or generated file. Before a response is stored,
  any occurrence of the token in the body is masked.
- The loaded value is registered with the logging redaction filter, which also
  masks anything shaped like an `rbuapp_` or `app_` token. The filter is
  attached to every log handler, so records from child loggers are covered.
- The request ledger and the rate-limit window are keyed by a fingerprint (the
  first 16 hex digits of the token's SHA-256), never the token.
- Deleting the stored token location (`forget-token`) is separate from
  deleting data. If the drive holding the token is lost or copied, the token
  is revoked or rotated at RepeaterBook.

## Regions and request limits (proposed)

**This section generalizes the approved-in-principle Washington-only design
and needs RepeaterBook's approval.** Until approved, the stricter original
numbers can be restored by editing `policy.py`.

### Region allowlist

| Code | Region | Parameters sent | Status |
|---|---|---|---|
| WA | Washington | `country=United States`, `state_id=53` | Enabled |
| OR | Oregon | `country=United States`, `state_id=41` | Enabled |
| ID | Idaho | `country=United States`, `state_id=16` | Enabled |
| BC | British Columbia | `country=Canada`, `state_id` unknown | **Disabled**: the documentation says `state_id` is "State / Province" and gives FIPS for US states, but does not give the identifier for a province. Refused until RepeaterBook confirms it. |

US `state_id` values are the Census FIPS codes, as the documentation's
"State ID (FIPS)" states. A region not in this table cannot be requested. There
is no all-regions, national or crawl mode.

### Limits

| Limit | Value |
|---|---|
| Regions per user action | At most 3, requested in sequence, never in parallel |
| HTTP requests per token | At most 4 in any rolling 24 hours, counted per request, not per action |
| Same region again | Not within 60 minutes of its last request |
| Budget check | If the remaining 24-hour budget cannot cover every requested region, the action fails before sending anything |
| Centre | Exactly one latitude,longitude |
| Radius | A whole number of miles from 1 through 60 (default 60) |
| Bands | At least one, each supported by the target radio |
| Candidates | At most 250 after local filtering, counted across all regions combined; 251 or more imports nothing |
| Pagination | None; the only query parameters are `country` and `state_id` |
| Concurrency | One refresh at a time, enforced by a process lock and a lock file |
| Timeout and size | 30 seconds; responses over 10 MiB are aborted |

The daily ceiling of four requests per token is unchanged from the original
design. A request is counted when it is attempted, before it is sent, so a
request that fails in flight still uses budget.

A request looks like this, with no other parameters:

```text
GET https://www.repeaterbook.com/api/export.php?country=United%20States&state_id=53
User-Agent: SignalWA/1.0 (+https://github.com/NiyaNagi/washington-sds150-favorites; ajamess@gmail.com)
X-RB-App-Token: rbuapp_...
Accept: application/json
```

## HTTP errors and 429 handling

Any failure stops the whole action: remaining regions are not requested, and
nothing is retried automatically.

| Response | Behavior |
|---|---|
| `200` with the documented export shape | Stored, filtered and staged |
| `200` that is not JSON with a `results` list | Nothing imported |
| `401`, `403`, or `auth_missing` / `auth_invalid` / `auth_inactive` / `auth_revoked` / `auth_scope_denied` / `ua_mismatch` in the body | Stop. The token is blocked locally until the operator corrects the cause and runs `unblock` (or configures a different token). Never retried. |
| `429` or `rate_limited` | Stop immediately. Refresh is locked until the later of `Retry-After` (seconds or an HTTP date) and 60 minutes from the response. |
| `400`, `404` | Stop and report the filter or endpoint problem |
| `408`, `425`, `500`, `502`, `503`, `504` | Stop; no same-action retry |
| Any redirect | Refused, so the token header can never follow it to another host |
| Unreachable host, timeout, connection reset, TLS failure, truncated body | Stop; recorded in the request ledger; no retry |
| Any other status | Stop |

Error messages name the status and the documented error code only. They never
quote the response body.

## Filtering and radio compatibility

Records are never copied directly into radio files. Each is filtered locally
and staged for review:

- great-circle distance from the one centre, within the radius;
- the output frequency inside a selected band the target radio can receive;
- analog FM only in this version; a digital-only repeater is dropped, never
  coerced to FM;
- a record without usable coordinates is rejected;
- nothing is synthesized: a missing input frequency, tone or coordinate stays
  missing, and a repeater without a published input becomes receive-only;
- off-air, unknown-status, closed/private, and input-less repeaters are
  flagged and applied only if the operator explicitly includes them;
- every drop is counted by reason and shown to the operator.

The documentation lists the data items the export returns but not their JSON
keys, so the adapter names them in one table (`normalize.FIELDS`) to be
confirmed against the first approved response. A record missing a needed key
is dropped with a stated reason, so a mismatch fails closed and shows up in
the drop summary rather than producing wrong channels.

Applied records carry their RepeaterBook id, retrieval date and attribution in
every channel note. They form a local-only list that is built from the store
at export time and never saved into the catalog, and it is marked
`licensed`, so the `--exclude-licensed` path that produces committable files
cannot include it (combining the two flags is refused).

## Cache and retention

RepeaterBook data lives in its own directory under the user's local
configuration home, `state/repeaterbook/`, apart from the shared HTTP cache:
that cache shares content-addressed blobs across URLs, so deleting one URL
there would leave the body on disk.

| Data | Rule |
|---|---|
| Raw responses | Fresh for 7 days; only fresh data can be re-filtered offline or applied. Deleted by day 30. |
| Staged candidates | Viewable, marked stale, after 7 days but never applied; deleted by day 30 |
| Applied records | Deleted 90 days after the data was retrieved. Only a new request, reviewed and applied again, restarts that clock; applying late or re-filtering cached data does not. |
| Request ledger | Deleted after 30 days |
| Review reports, and every file a `--with-repeaterbook` export writes (the programming file, its companion report, and `--copy-to` copies) | Registered, and deleted by day 90 |

Purges run at every startup of the CLI, and before and after every refresh,
including one that fails or is refused.
All retention is computed from an injected clock, so it is tested at exact
day boundaries.

**Delete All RepeaterBook Data** (CLI `delete-all --yes`, UI button) removes the
raw responses, staged candidates, applied records, the request ledger, and
every registered file: review reports, and everything a `--with-repeaterbook`
export wrote, including copies made with `--copy-to`. Channels already written
into a radio are outside the application's reach. It keeps only the rate-limit window and lockout timestamps
(token fingerprints and times, no RepeaterBook data), which expire on their
own within 24 hours; otherwise deleting data would reset the request budget.
**This is a deliberate choice for RepeaterBook to confirm.** Deleting the
token location is a separate action.

## Visible attribution and link-back

"Data courtesy of RepeaterBook.com", linked to `https://www.repeaterbook.com/`,
appears in:

- the UI panel, above the results table;
- every API response that carries RepeaterBook-derived records;
- CLI refresh, review, apply and records output;
- Markdown and HTML review reports, in a "Source and attribution" section;
- the companion report of any radio export that contains RepeaterBook-derived
  channels, in a "Source attribution" section;
- every applied channel's note.

The documentation asks for a link to the relevant detail page "when
practical" but does not give that page's URL form. Until RepeaterBook confirms
it, each record shows its RepeaterBook id and links to
`https://www.repeaterbook.com/`; switching to per-record links is one constant
in `policy.py`.

Binary radio formats with no suitable field carry no attribution; their
companion report does.

## Non-redistribution commitments

This project does not redistribute RepeaterBook data.

- Raw responses, the store, and the local configuration home are never
  committed.
- Tests use synthetic records only; none was ever returned by RepeaterBook.
- `tests/test_no_repeaterbook_data.py` fails if a committed catalog row,
  catalog channel or radio programming file cites a RepeaterBook repeater data
  page as its source.
- RepeaterBook-derived records can reach only the operator's own local export,
  never a redistributable one.
- No public website, API, proxy, shared service, map, directory or feed.

## Acceptance criteria and their tests

All tests are in `tests/test_repeaterbook.py` unless noted.

| # | Criterion | Tests |
|---|---|---|
| 1 | Every request sends the exact User-Agent with public URL and contact | `test_user_agent_is_the_approved_string_with_project_url_and_contact`, `test_request_sends_the_exact_user_agent_and_the_token_only_in_its_header`, `test_the_shared_default_user_agent_is_refused_before_sending` |
| 2 | Only a user-owned `rbuapp_` token, from an environment variable or an external file; no `app_` token; no repository-stored token | `test_token_prefix_rules`, `test_shared_app_token_is_rejected_without_quoting_it`, `test_rbuapp_token_is_accepted_and_never_shown`, `test_token_from_an_external_file`, `test_token_file_inside_the_repository_or_relative_is_refused`, `test_configuration_stores_only_where_the_token_is` |
| 3 | Token redaction | `test_token_never_reaches_the_store_logs_reports_or_config`, `test_errors_never_quote_the_token`, `test_log_redaction_masks_unregistered_tokens_from_child_loggers` |
| 4 | No live request without an explicit action | `test_update_all_makes_zero_repeaterbook_requests`, `test_generic_source_paths_refuse_repeaterbook`, `test_refresh_is_refused_while_disabled_with_the_pending_approval_message`, `test_refresh_is_refused_without_a_token`, `test_status_is_ready_only_with_both_the_flag_and_a_token`, `test_the_ui_lists_repeaterbook_but_greys_out_refresh_until_ready`, `test_normal_radio_export_never_calls_repeaterbook`, `test_global_offline_mode_refuses_a_live_refresh`, `test_web_routes` |
| 5 | No parallel requests | `test_a_second_refresh_while_one_runs_is_refused`, `test_another_process_lock_is_respected_and_a_stale_one_cleared`, `test_regions_are_requested_one_at_a_time_in_order` |
| 6 | Request limits per token | `test_exactly_one_request_per_region`, `test_the_same_region_is_not_requested_again_within_60_minutes`, `test_at_most_four_requests_in_any_rolling_24_hours`, `test_the_budget_is_checked_for_every_region_before_anything_is_sent`, `test_delete_all_does_not_reset_the_request_budget` |
| 7 | Allowlisted regions, one centre, radius 1-60, a supported band | `test_region_allowlist_and_its_verified_parameters`, `test_regions_outside_the_policy_are_refused_before_sending`, `test_radius_must_be_a_whole_number_from_1_to_60`, `test_radius_bounds_are_inclusive`, `test_exactly_one_valid_centre_is_required`, `test_bands_must_be_known_and_supported_by_the_radio`, `test_distance_is_great_circle`, `test_local_filtering_drops_rather_than_coerces` |
| 8 | At most 250 candidates, combined; 251 fails closed | `test_251_candidates_fail_closed_and_import_nothing`, `test_250_candidates_are_staged`, `test_the_cap_applies_to_the_combined_regions` |
| 9 | No pagination or parallel requests | `test_a_request_carries_only_the_region_parameters`, `test_regions_are_requested_one_at_a_time_in_order` |
| 10 | 429 stops with no retry and locks until the later of Retry-After and 60 minutes; authentication, scope and User-Agent errors are never retried | `test_429_locks_refresh_until_the_later_of_retry_after_and_60_minutes`, `test_retry_after_as_an_http_date`, `test_a_429_mid_action_stops_the_remaining_regions`, `test_auth_scope_and_user_agent_errors_block_until_the_operator_acts`, `test_transient_errors_stop_without_retry`, `test_bad_filter_or_endpoint_stops`, `test_redirects_are_refused_so_the_token_cannot_follow_one`, `test_a_response_that_is_not_the_export_shape_imports_nothing`, `test_429_lockout_is_measured_from_the_response_not_from_sending`, `test_transport_failures_are_classified_and_recorded`, `test_urllib_transport_turns_network_failures_into_transient_errors` |
| 11 | 7-day freshness, day-30 raw deletion, day-90 derived deletion, immediate deletion | `test_raw_is_fresh_for_7_days_after_which_it_cannot_be_applied`, `test_raw_responses_and_staging_are_deleted_by_day_30`, `test_applied_records_are_deleted_by_day_90_unless_reviewed_again`, `test_purges_run_before_a_refresh_and_at_startup`, `test_cli_startup_purges_expired_data`, `test_delete_all_removes_blobs_rows_ledger_and_reports`, `test_delete_all_removes_every_file_a_repeaterbook_export_wrote`, `test_a_late_apply_or_an_offline_refilter_does_not_extend_the_90_days`, `test_an_older_staged_copy_never_replaces_a_newer_retrieval`, `test_purge_runs_after_a_failed_refresh_too`, `test_forget_token_is_a_separate_action` |
| 12 | Generated files hold only programming fields, never raw bodies or credentials | `test_export_with_repeaterbook_holds_only_programming_fields`, `test_repeaterbook_records_never_go_into_a_redistributable_export`, `test_missing_input_tone_or_offset_is_never_synthesized` |
| 13 | Visible, linked attribution everywhere RepeaterBook data appears | `test_attribution_appears_in_every_output`, `test_staging_review_apply_carries_source_id_date_and_attribution`, `test_detail_links_use_the_home_page_until_the_url_form_is_confirmed`, `test_html_report_escapes_third_party_text` |
| 14 | Raw data is not committed, republished, sold or redistributed | `tests/test_no_repeaterbook_data.py` (all four tests), `test_the_reviewed_list_is_licensed_so_committable_exports_exclude_it`, `test_everything_lives_under_the_local_state_directory`, `test_the_in_repo_working_home_is_git_ignored` |

## Open questions for RepeaterBook

1. **Province identifier.** Which `state_id` value does `export.php` use for
   British Columbia (and other provinces)? BC stays disabled until this is
   known.
2. **Response keys.** The documentation lists the data items but not their
   JSON keys, and the list does not mention latitude and longitude. Does the
   North America export include coordinates, and under which keys? Without
   coordinates every record is rejected, by design.
3. **The multi-region budget.** Is up to three regions per action, four
   requests per rolling 24 hours per token, and 60 minutes between requests
   for the same region acceptable? Any stricter value you set will be used.
4. **Detail page links.** What URL form should a record's detail link use?
5. **Delete All and the rate limit.** Is it acceptable that Delete All keeps
   the request timestamps (no RepeaterBook data) until they expire, so a
   deletion cannot reset the request budget?
6. **Scope.** This application needs only `api.export`.
