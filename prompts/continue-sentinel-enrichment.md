# Reactivation Prompt: Complete Washington HPE Files from Local Sentinel

Use the following prompt from the repository root on the Sentinel machine:

```text
Resume the Washington SDS150 Favorites project from the latest main branch.

First read these files completely:
- docs/sentinel-machine-handoff.md
- docs/sentinel-completion-plan.md
- README.md
- CHANGELOG.md
- NOTICE.md
- docs/data-sources.md

Goal: use this machine's updated, local Uniden Sentinel HPDB to fill every
authoritative trunked-system gap and generate the most complete possible
personal Sentinel import pack. The current public baseline has 78 Favorites
List entries, 58 generated HPE files, 510 conventional channels, and 20
warnings. Seventeen warnings are Sentinel-dependent trunked lists; FL30 is
a rollup; FL45 and FL72 are intentional Discovery lists.

Work end-to-end rather than only proposing a plan:
1. Inspect the repository and confirm it is on the latest main branch.
2. Set up the Python environment and run the existing tests.
3. Ask me for the local Sentinel path only if you cannot locate hpdb.cfg.
   Prefer the Sentinel Database hpdb.cfg path; a scanner/card mount is also
   supported. Configure exactly one path.
4. Use --home .wasds150-home for all stateful wasds150 commands.
5. Read the Sentinel source in preview/read-only mode first, limited to
   sentinel_local. Report fact counts, coverage and conflicts without
   exposing or committing raw licensed content.
6. Investigate every unmatched target list. Fix generic matching,
   conversion or validation bugs in code when needed, using stable IDs and
   synthetic tests. Never hard-code licensed HPDB talkgroups, sites or
   control channels into the repository.
7. Preserve existing verified conventional systems in mixed lists.
8. Separate confirmed encrypted talkgroups into clearly named avoided
   departments while retaining them for change detection.
9. Apply the merge only after preview conflicts are resolved. Do not use
   --force without explaining each conflict and getting my approval.
10. Generate wasds150-output/sentinel-import-pack.zip and all loose HPEs.
11. Run the complete test suite, artifact validation, manifest/checksum
    validation, deterministic clean-wheel generation, and inspect the final
    warning list.
12. Target at least 75 valid HPE files with only FL30/FL45/FL72 unresolved;
    then build FL30 if it can be assembled safely, targeting 76 files and
    only the two Discovery warnings.
13. Verify git status contains no hpdb.cfg, s_*.hpd, HPE, local catalog,
    generated bundle, or preview JSON. Licensed/generated data stays local.
14. Commit and push only reusable code, synthetic tests and documentation.
15. Give me exact Sentinel import steps and identify any remaining gaps
    with evidence.

Do not claim completion based only on a lower warning count. Inspect the
actual systems, sites, frequencies, departments, talkgroups, service types,
locations, encryption avoids and generated HPE validation results.
```
