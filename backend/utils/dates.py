"""Date parsing and business-day helpers.

Used by the normalizer (parsing messy statement dates), the matcher (amount+date
and batch window checks), and the data generator (formatting).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d.%m.%Y",
    "%Y/%m/%d",
)


def parse_date(value) -> date | None:
    """Parse a date string in any supported format to a datetime.date."""
    if value is None or value == "":
        return None
    s = str(value).strip()
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def business_days_between(d1: date, d2: date) -> int:
    """Number of business days between two dates (weekends excluded)."""
    if d1 > d2:
        d1, d2 = d2, d1
    days = 0
    cur = d1
    while cur <= d2:
        if cur.weekday() < 5:
            days += 1
        cur += timedelta(days=1)
    return days


def within_business_days(window: int, d1: date, d2: date) -> bool:
    """True if the two dates are within `window` business days of each other."""
    return business_days_between(d1, d2) <= window


def iso_or_min(value) -> str:
    """Return the ISO date string, falling back to date.min for blank input."""
    d = parse_date(value) or date.min
    return d.isoformat()
