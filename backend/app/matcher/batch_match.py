"""Stage 4 — Batch-sum (many-to-one) match.

A single bank credit may represent the net sum of several settlement records
(impounded into one transferred amount). For a bank line with no single
matching settlement, search subsets of the remaining unmatched settlement pool
(within the date window) whose net amounts sum to the credit within tolerance.

- exactly one valid partition -> accept
- multiple valid partitions   -> BATCH_PARTITION_AMBIGUOUS
- none                        -> no partition

Bounded DP: we only consider settlements within the date window, keeping the
pool small (see constraints.md — never scan the whole dataset per line).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from backend.app.matcher.constants import (
    BATCH_WINDOW_BUSINESS_DAYS,
    DEFAULT_AMOUNT_TOLERANCE_PAISE,
    REVIEW_HIGH,
)

DATE_WINDOW_BUSINESS_DAYS = BATCH_WINDOW_BUSINESS_DAYS


@dataclass
class BatchResult:
    """Outcome of the batch-sum stage for one bank line."""

    status: str  # 'match' | 'ambiguous' | 'no_partition'
    settlement_ids: list[str] = field(default_factory=list)
    confidence: int = 0
    notes: list[str] = field(default_factory=list)


def _bank_date(normalized_line: dict) -> date:
    return date.fromisoformat(normalized_line.get("txn_date"))


def within_window(normalized_line: dict, settlement: dict, window_days: int) -> bool:
    from backend.utils.dates import within_business_days

    bank_d = _bank_date(normalized_line)
    s_date = date.fromisoformat(settlement.get("settlement_date"))
    return within_business_days(window_days, bank_d, s_date)


def _find_partitions(
    items: list[dict],
    target: int,
    tolerance: int,
    max_partitions: int = 2,
) -> list[list[dict]]:
    """Return up to `max_partitions` distinct subsets summing (within tol) to target.

    Standard sum-to-target subset enumeration over the (small) windowed pool.
    A valid subset is not extended further, so we capture minimal partitions.
    """
    n = len(items)
    found: list[list[dict]] = []

    def bt(start: int, total: int, chosen: list[dict]):
        if len(found) >= max_partitions:
            return
        if chosen and abs(total - target) <= tolerance:
            found.append(list(chosen))
            if len(found) >= max_partitions:
                return
            # Do not extend a valid subset; return to avoid supersets.
            return
        for i in range(start, n):
            it = items[i]
            nxt = total + it["net_amount"]
            if nxt > target + tolerance:
                continue
            chosen.append(it)
            bt(i + 1, nxt, chosen)
            chosen.pop()

    bt(0, 0, [])
    return found


def batch_match(
    normalized_line: dict,
    candidate_settlements: list[dict],
    tolerance_paise: int = DEFAULT_AMOUNT_TOLERANCE_PAISE,
    window_days: int = DATE_WINDOW_BUSINESS_DAYS,
) -> BatchResult:
    """Attempt a many-to-one batch match for the bank line."""
    credit_paise = normalized_line.get("credit_paise")
    if credit_paise is None:
        return BatchResult(status="no_partition", notes=["bank line is a debit"])

    # Constrain the pool to the date window (bound the combinatorial search).
    windowed = [s for s in candidate_settlements if within_window(normalized_line, s, window_days)]
    if not windowed:
        return BatchResult(status="no_partition", notes=["no settlements in date window"])

    partitions = _find_partitions(windowed, credit_paise, tolerance_paise, max_partitions=2)

    if len(partitions) == 1:
        ids = [p["settlement_id"] for p in partitions[0]]
        return BatchResult(
            status="match",
            settlement_ids=ids,
            confidence=REVIEW_HIGH,
            notes=[f"single batch-sum partition of {len(ids)} settlements"],
        )
    if len(partitions) > 1:
        return BatchResult(
            status="ambiguous",
            notes=["multiple valid batch-sum partitions (BATCH_PARTITION_AMBIGUOUS)"],
        )
    return BatchResult(status="no_partition", notes=["no subset sums to credit in window"])
