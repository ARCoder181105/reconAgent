"""Stage 3 — Amount + date match (no usable UTR).

When a bank line has no usable UTR, fall back to amount + date proximity. We
search the candidate settlement pool for records whose net amount matches the
bank credit within tolerance AND whose settlement date is within a ±2
business-day window.

- exactly one candidate  -> accept at medium confidence
- more than one          -> do NOT guess; flag ambiguous (MULTIPLE_CANDIDATES)
- none                   -> no candidate
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from backend.constants import STAGE_AMOUNT_DATE
from backend.app.matcher.constants import (
    DEFAULT_AMOUNT_TOLERANCE_PAISE,
    DEFAULT_WINDOW_BUSINESS_DAYS,
    REVIEW_HIGH,
    amount_close,
    within_business_days,
)

DATE_WINDOW_BUSINESS_DAYS = DEFAULT_WINDOW_BUSINESS_DAYS


@dataclass
class AmountDateResult:
    """Outcome of the amount+date stage for one bank line."""

    status: str  # 'match' | 'ambiguous' | 'no_candidate'
    settlement_id: str | None = None
    confidence: int = 0
    candidates: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _bank_date(normalized_line: dict) -> date:
    return date.fromisoformat(normalized_line.get("txn_date"))


def _settlement_date(normalized_settlement: dict) -> date:
    return date.fromisoformat(normalized_settlement.get("settlement_date"))


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def amount_date_match(
    normalized_line: dict,
    candidate_settlements: list[dict],
    tolerance_paise: int = DEFAULT_AMOUNT_TOLERANCE_PAISE,
    window_days: int = DATE_WINDOW_BUSINESS_DAYS,
) -> AmountDateResult:
    """Match a bank line against the settlement candidate pool by amount+date."""
    credit_paise = normalized_line.get("credit_paise")
    if credit_paise is None:
        return AmountDateResult(status="no_candidate", notes=["bank line is a debit, not a credit"])

    try:
        bank_d = _bank_date(normalized_line)
    except ValueError:
        return AmountDateResult(status="no_candidate", notes=["unparseable bank date"])

    hits: list[dict] = []
    for s in candidate_settlements:
        if not amount_close(s["net_amount"], credit_paise, tolerance_paise):
            continue
        s_date = _settlement_date(s)
        if not within_business_days(window_days, bank_d, s_date):
            continue
        hits.append(
            {
                "settlement_id": s["settlement_id"],
                "net_amount": s["net_amount"],
                "settlement_date": s["settlement_date"],
                "distance_business_days": _business_days(bank_d, s_date),
            }
        )

    if len(hits) == 1:
        return AmountDateResult(
            status="match",
            settlement_id=hits[0]["settlement_id"],
            confidence=REVIEW_HIGH,
            candidates=hits,
            notes=["single amount+date candidate, no UTR corroboration"],
        )
    if len(hits) > 1:
        return AmountDateResult(
            status="ambiguous",
            candidates=hits,
            notes=[f"{len(hits)} amount+date candidates; refusing to guess"],
        )
    return AmountDateResult(status="no_candidate", notes=["no amount+date candidate in window"])


def _business_days(d1: date, d2: date) -> int:
    from backend.utils.dates import business_days_between

    return business_days_between(d1, d2)
