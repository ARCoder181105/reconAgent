"""matcher package constants + shared types.

Central home for the confidence tiers, amount tolerance, date window, fuzzy
thresholds, and the ``MatchVerdict`` type. The domain vocabulary (stage keys,
reason codes) lives in ``backend/constants.py``; generic helpers live in
``backend/utils``. Re-exported here so matcher modules import from one place.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from backend.constants import (
    STAGE_EXACT,
    STAGE_FUZZY_UTR,
    STAGE_AMOUNT_DATE,
    STAGE_BATCH_SUM,
    STAGE_LLM_TIEBREAK,
)

# --- Confidence tiers (taxonomy.md) ---
AUTO_HIGH = 95      # exact UTR + exact amount
AUTO_LOW = 85       # fuzzy UTR (edit distance <= 2) + amount in tolerance
REVIEW_HIGH = 84    # amount+date single candidate / batch-sum single partition
REVIEW_LOW = 60

# --- Amount matching ---
DEFAULT_AMOUNT_TOLERANCE_PAISE = 100  # ± ₹1

# --- Date window (business days) for amount+date / batch stages ---
DEFAULT_WINDOW_BUSINESS_DAYS = 2
# A batch transfer aggregates settlements that trail behind the receipt date by
# up to several business days, so the batch pool uses a wider window than the
# amount+date stage (which stays tight to avoid false positives).
BATCH_WINDOW_BUSINESS_DAYS = 4

# --- Fuzzy UTR thresholds ---
FUZZY_MIN_SCORE = 0.85       # below this, do not accept
FUZZY_BORDELINE_SCORE = 0.85  # acceptable but low-confidence (review band)
FUZZY_AUTO_LOW_SCORE = 0.90
FUZZY_AUTO_HIGH_SCORE = 0.97

# Dominant-candidate recovery (It9): when no stage reaches the normal accept
# gate but ONE settlement is clearly the intended UTR match, accept it as a
# review-band signal. Guards: near-threshold best score + clear margin over the
# next-best (amount already within tolerance for the candidate to count).
FUZZY_DOMINANT_MIN_SCORE = 0.78
FUZZY_DOMINANT_MIN_RATIO = 1.5

# --- UTR token length bounds ---
UTR_MIN_LEN = 12
UTR_MAX_LEN = 18

UTR_TOKEN_RE = re.compile(rf"[A-Z0-9]{{{UTR_MIN_LEN},{UTR_MAX_LEN}}}")


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


# Re-exported shared helpers so matcher modules import from a single place.
from backend.utils.dates import business_days_between, within_business_days  # noqa: E402
from backend.utils.text import extract_utr_tokens  # noqa: E402


def amount_close(paise_a: int, paise_b: int, tolerance_paise: int = DEFAULT_AMOUNT_TOLERANCE_PAISE) -> bool:
    """True if the two paise amounts are within tolerance (±₹1 default)."""
    return abs(paise_a - paise_b) <= tolerance_paise
