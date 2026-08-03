"""Experimental direct SD-card installer.

Detect (:mod:`wasds150.installer.detect`), backup
(:mod:`wasds150.installer.backup`), write (:mod:`wasds150.installer.writer`,
gated by :mod:`wasds150.installer.confirm`), rollback
(:mod:`wasds150.installer.rollback`), and read-only HPDB inspection
(:mod:`wasds150.installer.hpdb_reader`) — all built on the strict path
allow-list in :mod:`wasds150.installer.paths` (``HPDB/`` is never on the
write/delete allow-list; the reader only ever reads it).

**This is the highest-risk component in wasds150**: it can write to real
user hardware. Every write is dry-run by default, requires an explicit
typed confirmation phrase, is preceded by a mandatory backup, and is
followed by post-write verification. Tests exercise this against simulated
volumes (plain directories under a test's ``tmp_path``) only — never real
hardware.
"""
