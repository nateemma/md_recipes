"""Total_Time parsing -- every form observed in the corpus (research R5)."""

import pytest

from src.timeparse import parse_total_time, to_iso8601


@pytest.mark.parametrize(
    "raw,minutes",
    [
        ("45 minutes", 45),
        ("30 minutes", 30),
        ("1 hour", 60),
        ("2 hours", 120),
        ("2 hours 30 minutes", 150),
        ("90 minutes", 90),
        ("2 days", 2880),
        ("8 days", 11520),
    ],
)
def test_definite_times(raw, minutes):
    tr = parse_total_time(raw)
    assert tr is not None
    assert tr.min_minutes == tr.max_minutes == minutes
    assert tr.is_definite


@pytest.mark.parametrize(
    "raw,lo,hi",
    [("3-5 hours", 180, 300), ("3-6 hours", 180, 360), ("6-8 hours", 360, 480)],
)
def test_ranges_keep_both_bounds(raw, lo, hi):
    tr = parse_total_time(raw)
    assert (tr.min_minutes, tr.max_minutes) == (lo, hi)
    assert not tr.is_definite


@pytest.mark.parametrize("raw", ["overnight", "", None, "   ", "when it's ready"])
def test_unparseable_yields_none_and_never_raises(raw):
    assert parse_total_time(raw) is None


@pytest.mark.parametrize(
    "raw,iso",
    [
        ("45 minutes", "PT45M"),
        ("1 hour", "PT1H"),
        ("2 hours", "PT2H"),
        ("2 hours 30 minutes", "PT2H30M"),
        ("2 days", "P2D"),
    ],
)
def test_iso8601_for_definite_times(raw, iso):
    assert to_iso8601(parse_total_time(raw)) == iso


@pytest.mark.parametrize("raw", ["3-5 hours", "overnight", ""])
def test_iso8601_omitted_when_uncertain(raw):
    """schema.org totalTime is a single Duration -- a range must be omitted, not guessed."""
    assert to_iso8601(parse_total_time(raw)) is None


def test_under_an_hour_uses_the_upper_bound():
    assert parse_total_time("45 minutes").max_minutes <= 60
    assert parse_total_time("3-5 hours").max_minutes > 60
