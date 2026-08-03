"""Generic, reusable parser: baseline catalog free text -> explicit channels.

**Why this exists** (see finding #1 in the audit that produced this
module): every baseline ``FavoritesList.departments_or_channels`` value is
hand-authored prose, not a machine-delimited channel list (see
:mod:`wasds150.models.catalog`'s module docstring). But a *lot* of that
prose already spells out literal, explicit frequencies the human curators
copied from a cited public source (NOAA, USCG, FCC, FAA, WA MIL, ARRL,
...) — e.g. ``"Ch16 156.800(distress)"`` or ``"KXI27 Forks162.425"``. This
module extracts exactly those already-checked-in literal numbers into
structured :class:`ParsedChannel` records, so :mod:`wasds150.recipes` can
turn them into a real :class:`~wasds150.models.catalog.System` — **without
ever inventing a number that was not already present in the reviewed
text**.

**Non-fabrication discipline** — the parser only ever promotes a
frequency it finds *literally spelled out* in the source text:

* A bare hyphen-joined pair (``"866.5125-868.0125"``) reads as a *range*
  description, not a single channel — the whole clause is skipped and
  reported via :attr:`ChannelParseResult.skipped_ranges` rather than
  guessed at (no interpolation of "channels in between").
* A slash-joined list (``"151.820/151.880/151.940"``) is a literal,
  explicit enumeration — each value becomes its own channel.
* Text with no explicit ``NN.NNN``-shaped number at all (a bare channel
  number, a trunked-system mention, a service description) produces
  nothing — never a placeholder, never a guess.
* Values that are actually something else entirely (a CTCSS/DCS tone, a
  wattage rating like ``"0.5W"``, a band nickname like ``"1.25m"``) are
  recognized and excluded so they can never be mistaken for a channel
  frequency (see :data:`_FREQ_TOKEN_RE` and :data:`_TONE_RE`).

**Known, accepted limitation**: label text is extracted heuristically
(text immediately preceding a frequency, honoring parentheses as
"supplementary detail" rather than a new label). ``/`` is used in this
catalog's prose for at least three different things (joining two distinct
channel mentions, joining several frequencies of the same named group, or
as plain punctuation inside a description like ``"deck/shore"``) that
cannot always be told apart by a general-purpose parser — labels may
occasionally be slightly imprecise (e.g. truncated to the last segment of
a compound name). This never affects the frequency value itself, only the
cosmetic label, and is an accepted tradeoff over hand-authoring per-row
overrides (see :mod:`wasds150.sources.static_seeds` for the handful of
rows where a hand-curated table is used instead because the prose only
gives a range).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

#: CTCSS ("PL"/private line, historically Motorola's trademark for the
#: same thing) or DCS tone mentions -- extracted and removed before
#: frequency scanning so e.g. "PL127.3" is never mistaken for a channel at
#: 127.3 MHz.
_TONE_RE = re.compile(r"\b(?:PL|CTCSS)\s*(\d{1,3}(?:\.\d{1,2})?)\b|\bDCS[- ]?(\d{2,3})\b", re.IGNORECASE)

#: A single explicit MHz-shaped number: 1-4 digits, a literal decimal
#: point, 1-5 digits. The lookbehind/lookahead pair ensures this matches a
#: *complete* number (never the tail of a longer one) regardless of
#: whether it is glued directly to surrounding text (``"Forks162.425"``)
#: or not. Never matches a number immediately followed by a letter (a
#: wattage rating like ``"0.5W"``, a band nickname like ``"1.25m"``, or
#: any other non-frequency unit) -- every real frequency in this catalog's
#: text is followed by whitespace or punctuation, never a bare letter.
_FREQ_TOKEN_RE = re.compile(r"(?<![\d.])\d{1,4}\.\d{1,5}(?!\d)(?![A-Za-z])")

#: A literal range: two frequency-shaped numbers joined by a bare hyphen
#: and nothing else. Recognized so it can be *excluded* (never expanded
#: into individual channels) -- interpolating "the channels in between" a
#: cited range would be exactly the kind of fabrication this module must
#: never do.
_RANGE_RE = re.compile(
    rf"{_FREQ_TOKEN_RE.pattern}\s*-\s*{_FREQ_TOKEN_RE.pattern}"
)

#: A literal, explicit list: two or more frequency-shaped numbers joined
#: only by slashes (never a range -- see module docstring).
_SLASH_CLUSTER_RE = re.compile(
    rf"{_FREQ_TOKEN_RE.pattern}(?:\s*/\s*{_FREQ_TOKEN_RE.pattern})+"
)

#: Characters that, read right-to-left from a frequency, mark "the label
#: ends here, a new distinct mention begins" for a *standalone* token
#: (never applied to a multi-value cluster's shared base label -- see
#: :func:`_expand_indexed_labels`, which would otherwise have its own
#: numbering destroyed by this same cut).
_CUT_AFTER_CHARS = "/+,"


@dataclass(frozen=True)
class ParsedChannel:
    """One literal channel extracted from free text: a label plus a
    frequency that was spelled out verbatim in the source (never
    interpolated/guessed)."""

    label: str
    freq_mhz: float
    tone: str = ""
    note: str = ""


@dataclass
class ChannelParseResult:
    channels: List[ParsedChannel] = field(default_factory=list)
    #: Raw ``"NNN.NNNN-NNN.NNNN"``-shaped substrings that were recognized
    #: as ranges and deliberately *not* expanded into channels.
    skipped_ranges: List[str] = field(default_factory=list)


def _split_top_level(text: str, delimiters: str) -> List[str]:
    """Split ``text`` on any character in ``delimiters``, but only outside
    parentheses -- several rows use a parenthetical that itself contains a
    comma (e.g. ``"(D1 Pierce,D2 King)"``), which must stay one piece."""
    parts: List[str] = []
    depth = 0
    current: List[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth = max(0, depth - 1)
            current.append(ch)
        elif depth == 0 and ch in delimiters:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p for p in (part.strip() for part in parts) if p]


def _trailing_note(piece: str) -> "tuple[str, str]":
    """Strip a trailing ``(...)`` block and return ``(remaining, note)`` --
    but only if that block contains no frequency-shaped number itself
    (otherwise it is not a plain annotation, e.g. ``"Ch7(462.7125,...)"``
    keeps its frequency data available for the scan below)."""
    match = re.search(r"\(([^()]*)\)\s*$", piece)
    if not match:
        return piece, ""
    inner = match.group(1)
    if _FREQ_TOKEN_RE.search(inner):
        return piece, ""
    return piece[: match.start()].rstrip(), inner.strip()


def _open_paren_starts(text: str) -> List[int]:
    """``result[i]`` = index of the innermost ``(`` still open at position
    ``i`` (or ``-1``). Lets label extraction tell "this frequency is
    *inside* a still-open paren (the paren holds a numeric detail about
    the preceding bare label)" apart from "this frequency follows a
    *closed* paren (which is part of the label, e.g. a clarifying place
    name)."""
    result = [-1] * (len(text) + 1)
    stack: List[int] = []
    for i, ch in enumerate(text):
        result[i] = stack[-1] if stack else -1
        if ch == "(":
            stack.append(i)
        elif ch == ")" and stack:
            stack.pop()
    result[len(text)] = stack[-1] if stack else -1
    return result


def _cut_after(segment: str) -> str:
    """Standalone-token label cleanup: drop everything up to and including
    the last ``/``, ``+`` or ``,`` (each marks a new distinct mention in
    this catalog's prose -- see module docstring)."""
    idx = max((segment.rfind(c) for c in _CUT_AFTER_CHARS), default=-1)
    label = segment[idx + 1:] if idx >= 0 else segment
    return label.strip(" \t.,")


def _raw_label(working: str, start: int, prev_end: int, paren_starts: List[int]) -> str:
    open_at = paren_starts[start]
    boundary = open_at if open_at != -1 and open_at >= prev_end else start
    return working[prev_end:boundary]


def _expand_indexed_labels(raw_label: str, count: int) -> Optional[List[str]]:
    """For a multi-value cluster, try to derive a precise per-channel label
    from a numeric pattern already present in ``raw_label`` itself:
    a hyphen range (``"SAR1-5"`` -> ``SAR1``..``SAR5``) or a bare
    slash-separated integer list (``"CEMNET-1/2/3"`` -> ``CEMNET-1``,
    ``CEMNET-2``, ``CEMNET-3``). Returns ``None`` (never a guess) if no
    such pattern is found *with a matching count* -- the caller falls back
    to a generic ``"label"``, ``"label (2)"``, ... suffix instead."""
    if count == 1:
        return [_cut_after(raw_label) or raw_label.strip()]
    match = re.search(r"(\d+)\s*-\s*(\d+)", raw_label)
    if match:
        start, end = int(match.group(1)), int(match.group(2))
        if end - start + 1 == count:
            return [raw_label[: match.start()] + str(start + i) + raw_label[match.end():] for i in range(count)]
    match2 = re.search(r"(?:(?<=\D)|^)(\d+(?:/\d+){%d})(?:\D|$)" % (count - 1), raw_label)
    if match2:
        numbers = match2.group(1).split("/")
        if len(numbers) == count:
            return [raw_label[: match2.start(1)] + n + raw_label[match2.end(1):] for n in numbers]
    return None


def _parse_piece(piece: str) -> ChannelParseResult:
    result = ChannelParseResult()
    working = piece

    tone = ""
    tone_match = _TONE_RE.search(working)
    if tone_match:
        tone = f"CTCSS {tone_match.group(1)}" if tone_match.group(1) else f"DCS {tone_match.group(2)}"
        working = working[: tone_match.start()] + " " + working[tone_match.end():]

    working, note = _trailing_note(working)
    paren_starts = _open_paren_starts(working)

    def _range_repl(match: "re.Match[str]") -> str:
        result.skipped_ranges.append(match.group(0).strip())
        return " " * len(match.group(0))

    working = _RANGE_RE.sub(_range_repl, working)

    consumed = [False] * len(working)
    for match in _SLASH_CLUSTER_RE.finditer(working):
        freqs = [float(x) for x in re.findall(r"\d{1,4}\.\d{1,5}", match.group(0))]
        raw_label = _raw_label(working, match.start(), 0, paren_starts)
        labels = _expand_indexed_labels(raw_label, len(freqs))
        if labels is None:
            base = raw_label.strip(" \t.,") or note or piece.strip()
            labels = [base] + [f"{base} ({i})" for i in range(2, len(freqs) + 1)]
        for label, freq_mhz in zip(labels, freqs):
            result.channels.append(
                ParsedChannel(label=label.strip() or note or piece.strip(), freq_mhz=freq_mhz, tone=tone, note=note)
            )
        for i in range(match.start(), match.end()):
            consumed[i] = True

    prev_end = 0
    for match in _FREQ_TOKEN_RE.finditer(working):
        if any(consumed[match.start():match.end()]):
            continue
        raw_label = _raw_label(working, match.start(), prev_end, paren_starts)
        label = _cut_after(raw_label) or note or piece.strip()
        result.channels.append(ParsedChannel(label=label, freq_mhz=float(match.group(0)), tone=tone, note=note))
        prev_end = match.end()

    return result


def parse_department_text(text: str) -> ChannelParseResult:
    """Parse a ``departments_or_channels``-shaped free-text field into
    explicit :class:`ParsedChannel` records.

    ``text`` is split on top-level ``;`` then ``,`` (paren-aware -- a
    parenthetical's own internal commas never split it), and each
    resulting piece is scanned independently. Never raises; malformed or
    prose-only text simply yields no channels.
    """
    result = ChannelParseResult()
    if not text:
        return result
    for segment in _split_top_level(text, ";"):
        for piece in _split_top_level(segment, ","):
            piece_result = _parse_piece(piece)
            result.channels.extend(piece_result.channels)
            result.skipped_ranges.extend(piece_result.skipped_ranges)
    return result
