"""Export/bundle builders.

Only formats that don't require reverse-engineering the undocumented .hpe
binary format are implemented here: CSV (byte-compatible with the existing
catalog CSV shape), a machine-generated Markdown summary, and a
"Sentinel import pack" zip that is the guaranteed-safe path to get a
generated profile into Sentinel today (manual "Append to Favorites List"),
pending the HPE codec research (:mod:`wasds150.hpe`).
"""
