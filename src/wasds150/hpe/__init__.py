"""The Uniden `.hpe`/`.hpd` container/record engine.

* :mod:`wasds150.hpe.codec` — the `.hpe` container transform
  (XOR 0x0C <-> gzip <-> text), with decompression-bomb and byte-range
  guards, and dialect detection.
* :mod:`wasds150.hpe.record` — a generic, lossless tab-record parser that
  preserves every field (known or not) byte-for-byte.
* :mod:`wasds150.hpe.schema` — the BCDx36HP field/arity tables and
  service-type/tone vocabulary, with per-entry provenance (verified against
  a real fixture vs. report-citation-only).
* :mod:`wasds150.hpe.builders` — canonical wasds150 model ->
  Conventional/Trunk record trees.
* :mod:`wasds150.hpe.flist` — `f_list.cfg` read/patch helpers.
* :mod:`wasds150.hpe.hpdb` — read-only HPDB (on-card RadioReference
  database) parser, system segmentation, county/geo lookup, and
  HPDB-to-Favorites dialect conversion.
* :mod:`wasds150.hpe.tree` — best-effort display-only hierarchy grouping.

See ``NOTICE.md`` for the full research attribution and licensing
discipline followed while implementing this package: every module here is
an original Python 3.9 implementation written from documented facts, not
copied from any GPL-licensed or unlicensed reference project.
"""
