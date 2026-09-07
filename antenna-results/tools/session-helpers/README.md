# Archived August 2026 session helpers

These files are byte-for-byte transcriptions of the surviving local helper
scripts inspected while documenting the August 2026 antenna sessions:

- `capture_scanner_zooms.py`
- `retest_bands.py`
- `verify_load.py`

They are preserved for audit completeness. They are **not** recommended entry
points:

- imports assume `nanovna_swr.py` is in the same directory;
- `retest_bands.py` and `verify_load.py` contain hard-coded 2026 paths;
- they predate the fail-closed validator and hardened acquisition wrapper;
- the final August 23 and August 28 installed-system reports did not depend on
  these helpers.

For new work use:

- `../nanovna_swr.py`
- `../validate_nanovna_run.py`
- the deployment-specific deterministic report generator.
