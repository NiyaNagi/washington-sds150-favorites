"""Pluggable catalog sources.

Only :mod:`wasds150.sources.static_pack` (this repo's checked-in CSV) is
implemented. The other adapters in this package are placeholders that
define the intended interface but intentionally raise ``NotImplementedError``
— they are pending separate research (Sentinel local DB format,
RadioReference free/premium access, NOAA/RepeaterBook APIs) and are out of
scope for this phase. See :mod:`wasds150.sources.base` for the contract they
will implement, and :mod:`wasds150.sources.registry` for how they are
discovered.
"""
