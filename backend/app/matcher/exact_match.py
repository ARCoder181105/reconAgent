"""Stage 1 — Exact UTR match.

Full UTR found as a substring inside the bank description OR ref_no, AND the
settlement net amount matches the bank credit within tolerance. Confidence 100.
"""
from __future__ import annotations

from backend.constants import STAGE_EXACT
from backend.app.matcher.constants import (
    AUTO_HIGH,
    DEFAULT_AMOUNT_TOLERANCE_PAISE,
    MatchVerdict,
    amount_close,
)


def exact_match(
    normalized_settlement: dict,
    normalized_line: dict,
    tolerance_paise: int = DEFAULT_AMOUNT_TOLERANCE_PAISE,
) -> MatchVerdict:
    """Judge whether the settlement exactly matches the bank line.

    Telephone-haystack: the UTR must appear verbatim as a substring.
    """
    utr = normalized_settlement.get("utr", "")
    if not utr:
        return MatchVerdict(stage=STAGE_EXACT, matched=False, notes=["settlement has no UTR"])

    blob = f"{normalized_line.get('description', '')} {normalized_line.get('ref_no', '')}"
    if utr not in blob:
        return MatchVerdict(
            stage=STAGE_EXACT,
            matched=False,
            notes=["UTR not found verbatim in description/ref_no"],
        )

    if not amount_close(normalized_settlement["net_amount"], normalized_line.get("credit_paise") or 0, tolerance_paise):
        return MatchVerdict(
            stage=STAGE_EXACT,
            matched=False,
            notes=["UTR present but amount out of tolerance"],
        )

    return MatchVerdict(stage=STAGE_EXACT, matched=True, confidence=AUTO_HIGH, score=1.0)
