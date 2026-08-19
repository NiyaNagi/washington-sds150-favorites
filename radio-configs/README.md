# Generated radio configurations

Programming files built from this repository's own catalog, committed so they
can be picked up and loaded without running the toolchain first.

| File | Radio | Contents |
|---|---|---|
| `h9-ozette.csv` | TIDRADIO TD-H9 | 185 memories, CHIRP Generic CSV |
| `h9-ozette-report.md` | | Human-readable memory map |
| `ftx1-wa.FTX1` | Yaesu FTX-1 | 959 memories + 47 scan pairs, native format |
| `ftx1-wa-report.md` | | Human-readable memory map |

Everything here is **generated**. The catalog is the source of truth, so these
files go stale the moment the catalog changes. Regenerate with:

```bash
wasds150 --home .wasds150-home plan export h9-ozette --out radio-configs
wasds150 --home .wasds150-home plan export ftx1-wa --target ftx1-file --out radio-configs
```

## Provenance

These are built only from data already committed to this repository - the
catalog modules under `src/wasds150/catalog/`, each channel carrying its source
URL. No vendor database, no licensed Sentinel or RadioReference content, and no
per-channel text from the RT Systems programmer is present. See
[`NOTICE.md`](../NOTICE.md) for the redistribution posture per source.

## Loading them

- **TD-H9** - import the CSV in CHIRP and upload, or use
  `scripts/radios/program_tdh9.py`. See
  [the programming guide](../docs/td-h9-programming.md).
- **FTX-1** - open the `.FTX1` directly in the RT Systems programmer.

The FTX-1 profile is **unverified against hardware**: it was built from
documentation, and the generated file has been checked against a hand-merged
reference file but never written to a radio. Review it in the programmer
before trusting it.
