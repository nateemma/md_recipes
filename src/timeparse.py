"""Free-text Total_Time -> a range of minutes -> ISO 8601.

Defensive by design. The corpus currently has a value in all 211 files (research
R5), but the parse must never fail the build and never guess: unrecognised means
"no time known", which is a valid state, not an error (FR-012).
"""

from __future__ import annotations

import re

from .model import TimeRange

_UNITS = {
    "minute": 1,
    "minutes": 1,
    "min": 1,
    "mins": 1,
    "hour": 60,
    "hours": 60,
    "hr": 60,
    "hrs": 60,
    "day": 1440,
    "days": 1440,
}

# "45 minutes", "2 hours", "1 hour"
_SIMPLE = re.compile(r"(\d+)\s*([A-Za-z]+)")
# "3-5 hours", "6 - 8 hours"
_RANGE = re.compile(r"(\d+)\s*[-–—]\s*(\d+)\s*([A-Za-z]+)")


def parse_total_time(raw: str | None) -> TimeRange | None:
    """Parse the corpus's observed forms. Anything else yields None."""
    if not raw:
        return None
    text = raw.strip().lower()
    if not text:
        return None

    # A range first -- "3-5 hours" would otherwise match _SIMPLE as just "3".
    m = _RANGE.search(text)
    if m:
        unit = _UNITS.get(m.group(3))
        if unit is None:
            return None
        lo, hi = int(m.group(1)) * unit, int(m.group(2)) * unit
        return TimeRange(min(lo, hi), max(lo, hi))

    # One or more "N unit" pairs, summed: "2 hours 30 minutes" -> 150.
    total = 0
    found = False
    for count, word in _SIMPLE.findall(text):
        unit = _UNITS.get(word)
        if unit is None:
            continue
        total += int(count) * unit
        found = True
    if not found:
        return None  # "overnight", and anything else unrecognised
    return TimeRange(total, total)


def to_iso8601(tr: TimeRange | None) -> str | None:
    """ISO 8601 duration, but only for a definite time.

    schema.org's totalTime is a single Duration with nowhere to express
    uncertainty, so a range is omitted rather than reported as one of its
    endpoints or as a midpoint the source never claimed.
    """
    if tr is None or not tr.is_definite:
        return None
    minutes = tr.min_minutes
    if minutes <= 0:
        return None
    if minutes % 1440 == 0:
        return f"P{minutes // 1440}D"
    hours, mins = divmod(minutes, 60)
    out = "PT"
    if hours:
        out += f"{hours}H"
    if mins:
        out += f"{mins}M"
    return out
