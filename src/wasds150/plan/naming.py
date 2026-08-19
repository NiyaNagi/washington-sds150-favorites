"""Deterministic channel-name shortening.

A TD-H9 shows eight characters; an FTX-1 shows twelve; the SDS150 shows a
full label.  Catalog labels are written for humans reading documentation
("Olympic National Park Dispatch"), so targeting a small display means
abbreviating - and abbreviating badly is worse than useless, because on a
handheld the name is the *only* thing identifying what you are hearing.

The rules here are deliberately boring and total: the same label always
shortens to the same string, and two different labels never collide silently.
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Set

#: Words that carry no identifying information once a name is squeezed.
_FILLER = {
    "A", "AN", "AND", "AT", "FOR", "OF", "ON", "THE", "TO", "WITH",
    "AREA", "CHANNEL", "CH", "FREQUENCY", "SYSTEM", "SERVICE", "RADIO",
    "COUNTY", "NATIONAL", "STATE", "REGIONAL", "REGION",
}

#: Long words with a conventional short form.  Applied before vowel removal
#: so the result stays readable.
_ABBREVIATIONS = {
    "AIRPORT": "ARPT",
    "AVIATION": "AVN",
    "COMMAND": "CMD",
    "COMMON": "COM",
    "DEPARTMENT": "DEPT",
    "DISPATCH": "DISP",
    "EMERGENCY": "EMER",
    "FEDERAL": "FED",
    "FOREST": "FRST",
    "HOSPITAL": "HOSP",
    "INTEROP": "IOP",
    "INTEROPERABILITY": "IOP",
    "MANAGEMENT": "MGMT",
    "MOUNTAIN": "MTN",
    "MUTUAL": "MUT",
    "NORTH": "N",
    "OLYMPIC": "OLY",
    "OPERATIONS": "OPS",
    "PARK": "PK",
    "PATROL": "PTRL",
    "PENINSULA": "PEN",
    "POLICE": "PD",
    "PRIMARY": "PRI",
    "REPEATER": "RPT",
    "RESCUE": "RESQ",
    "SEARCH": "SAR",
    "SHERIFF": "SO",
    "SOUTH": "S",
    "TACTICAL": "TAC",
    "TRIBAL": "TRB",
    "WEATHER": "WX",
    "WEST": "W",
    "EAST": "E",
}

_NON_WORD = re.compile(r"[^A-Za-z0-9]+")


def _words(label: str) -> List[str]:
    return [w for w in _NON_WORD.split(label.upper()) if w]


def _devowel(word: str) -> str:
    """Drop interior vowels, keeping the first character and all digits."""
    if len(word) <= 2:
        return word
    head, tail = word[0], word[1:]
    stripped = "".join(ch for ch in tail if ch not in "AEIOU" or ch.isdigit())
    return head + (stripped or tail)


def _has_digit(word: str) -> bool:
    return any(ch.isdigit() for ch in word)


def _compose(words: List[str], max_len: int) -> str:
    """Build a name in word order, protecting the identifying parts.

    Words containing digits are never shortened.  A channel number, a
    frequency fragment or the digit in a callsign is usually the single most
    distinguishing thing about a channel, so the budget is spent on the words
    around them: first by dropping vowels, then by dropping whole trailing
    words, and only as a last resort by truncating.
    """
    locked = [w for w in words if _has_digit(w)]
    reserved = sum(len(w) for w in locked)
    if reserved >= max_len:
        return "".join(locked)[:max_len]

    # Track a shortened form per word, keeping positions so the result reads
    # in the same order as the label.
    parts = [w if _has_digit(w) else _devowel(w) for w in words]

    def total() -> int:
        return sum(len(p) for p in parts)

    # Drop whole trailing words that are not carrying digits.
    while total() > max_len:
        droppable = [i for i, w in enumerate(words) if not _has_digit(w) and parts[i]]
        if len(droppable) <= 1:
            break
        parts[droppable[-1]] = ""

    # Then trim whatever single flexible word is left.
    if total() > max_len:
        flexible = [i for i, w in enumerate(words) if not _has_digit(w) and parts[i]]
        if flexible:
            index = flexible[0]
            allowance = max_len - (total() - len(parts[index]))
            parts[index] = parts[index][: max(allowance, 0)]

    dropped = "".join(parts)[:max_len]

    # Dropping whole words can leave the budget underspent. A plain
    # truncation often reads better - "USFSARGR" beats "USFSAR" - but only if
    # it does not cut away a digit that identifies the channel.
    truncated = "".join(w if _has_digit(w) else _devowel(w) for w in words)[:max_len]
    if len(truncated) > len(dropped) and all(w in truncated for w in locked):
        return truncated
    return dropped


def _candidates(label: str, max_len: int) -> Iterable[str]:
    words = _words(label)
    if not words:
        return

    # 1. The label itself, if it already fits.
    joined = "".join(words)
    yield joined

    # 2. Drop filler words, but never drop everything.
    meaningful = [w for w in words if w not in _FILLER] or words
    yield "".join(meaningful)

    # 3. Apply conventional abbreviations.
    abbreviated = [_ABBREVIATIONS.get(w, w) for w in meaningful]
    yield "".join(abbreviated)

    # 4. Remove interior vowels from the longer words.
    yield "".join(_devowel(w) for w in abbreviated)

    # 5. Spend the remaining budget around the identifying words.
    yield _compose(abbreviated, max_len)


def _filter_charset(text: str, charset: Optional[str]) -> str:
    if charset is None:
        return text
    allowed = set(charset)
    return "".join(ch for ch in text if ch in allowed)


def shorten_name(
    label: str,
    max_len: int,
    *,
    charset: Optional[str] = None,
    fallback: str = "CH",
) -> str:
    """Shorten ``label`` to at most ``max_len`` characters.

    This does not attempt to make the result unique; use :class:`NameAllocator`
    when several channels share a display.
    """
    if max_len <= 0:
        raise ValueError("max_len must be positive")

    best = ""
    for candidate in _candidates(label, max_len):
        candidate = _filter_charset(candidate, charset)
        if not candidate:
            continue
        if len(candidate) <= max_len:
            return candidate
        # Remember the shortest over-long candidate to truncate as a last resort.
        if not best or len(candidate) < len(best):
            best = candidate

    if best:
        return best[:max_len]
    return _filter_charset(fallback, charset)[:max_len] or fallback[:max_len]


class NameAllocator:
    """Hands out unique display names for one radio.

    Collisions are resolved by appending an incrementing suffix, shrinking the
    stem to make room.  Because allocation is order-dependent, the first
    channel to claim a name keeps it, which makes a plan's output stable as
    long as the plan's ordering is stable.
    """

    def __init__(self, max_len: int, *, charset: Optional[str] = None) -> None:
        self.max_len = max_len
        self.charset = charset
        self._taken: Set[str] = set()
        self._assigned: Dict[str, str] = {}

    def allocate(self, label: str, *, key: Optional[str] = None) -> str:
        if key is not None and key in self._assigned:
            return self._assigned[key]

        stem = shorten_name(label, self.max_len, charset=self.charset)
        name = stem
        suffix = 1
        while name in self._taken:
            suffix += 1
            tag = str(suffix)
            if len(tag) >= self.max_len:
                raise ValueError(f"cannot make {label!r} unique in {self.max_len} chars")
            name = stem[: self.max_len - len(tag)] + tag

        self._taken.add(name)
        if key is not None:
            self._assigned[key] = name
        return name
