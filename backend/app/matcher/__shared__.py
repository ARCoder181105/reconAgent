"""Shared helpers for the matching engine.

Defines the normalized-record shapes, the stage verdict type, and shared
primitives (amount tolerance, UTR token extraction, business-day windows).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

# Canonical stage keys (match taxonomy.md).
STAGE_EXACT = "exact"
STAGE_FUZZY = "fuzzy_utr"
STAGE_AMOUNT_DATE = "amount_date"
STAGE_BATCH = "batch_sum"
STAGE_LLM = "llm_tiebreak"

# A UTR-like token: 12-18 alphanumeric run (our generator emits 16 chars).
UTR_TOKEN_RE = re.compile(r"[A-Z0-9]{12,18}")

# Amount tiers from taxonomy.md.
AUTO_HIGH = 95
AUTO_LOW = 85
REVIEW_HIGH = 84
REVIEW_LOW = 60


@dataclass
class MatchVerdict:
    """Result of a single settlement<->bank-line comparison.

    ``matched`` is False when the pair should not be closed by this stage.
    ``confidence`` is 0-100. Extra context (edit distance, which UTR token) is
    kept in ``notes`` for the exception-reason trail.
    """

    stage: str
    matched: bool
    confidence: int = 0
    score: float = 0.0
    notes: list[str] = field(default_factory=list)


def amount_close(paise_a: int, paise_b: int, tolerance_paise: int = 100) -> bool:
    """True if the two paise amounts are within tolerance (±₹1 default)."""
    return abs(paise_a - paise_b) <= tolerance_paise


def extract_utr_tokens(text: str) -> list[str]:
    """Return UTR-like tokens found in a freetext string (uppercased)."""
    if not text:
        return []
    return UTR_TOKEN_RE.findall(text.upper())


def business_days_between(d1: date, d2: date) -> int:
    """Number of business days between two dates (weekends excluded). Simple."""
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
