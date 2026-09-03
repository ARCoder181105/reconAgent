"""Stage 2 — Fuzzy UTR match.

When the UTR is truncated, embedded mid-string, or slightly garbled, exact
substring fails. This stage extracts UTR-like tokens from the bank text and
scores them against the expected UTR via rapidfuzz edit distance, with explicit
truncation-aware prefix/suffix checks. A candidate is only accepted if the
amount also falls within tolerance.

Confidence scales with edit distance and amount closeness (taxonomy.md).
"""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from backend.app.matcher.__shared__ import (
    AUTO_HIGH,
    AUTO_LOW,
    REVIEW_HIGH,
    STAGE_FUZZY,
    MatchVerdict,
    UTR_TOKEN_RE,
    amount_close,
)


def _truncation_score(expected_utr: str, token: str) -> float:
    """Best similarity treating the token as a truncated prefix or suffix.

    Returns a 0..1 score. If token length <= expected, we compare the token
    against expected[:len] and expected[-len:]. Otherwise fall back to ratio.
    """
    exp = expected_utr
    tok = token
    n = min(len(exp), len(tok))
    if n == 0:
        return 0.0
    prefix_hit = fuzz.ratio(exp[:n], tok[:n]) / 100.0
    suffix_hit = fuzz.ratio(exp[-n:], tok[-n:]) / 100.0
    return max(prefix_hit, suffix_hit)


def _candidate_tokens(normalized_line: dict) -> list[str]:
    """Collect UTR-like tokens from description and ref_no."""
    tokens: set[str] = set()
    blob = f"{normalized_line.get('description', '')} {normalized_line.get('ref_no', '')}"
    tokens.update(UTR_TOKEN_RE.findall(blob))
    # Also include raw alphanumeric runs in ref_no (may already be short).
    for piece in re.split(r"[\s/\-,.]+", blob):
        if re.fullmatch(r"[A-Z0-9]{8,18}", piece):
            tokens.add(piece)
    return sorted(tokens)


def fuzzy_match(normalized_settlement: dict, normalized_line: dict, tolerance_paise: int = 100) -> MatchVerdict:
    """Judge a fuzzy UTR match for the settlement against the bank line."""
    utr = normalized_settlement.get("utr", "")
    if not utr:
        return MatchVerdict(stage=STAGE_FUZZY, matched=False, notes=["settlement has no UTR"])

    if not amount_close(normalized_settlement["net_amount"], normalized_line.get("credit_paise") or 0, tolerance_paise):
        return MatchVerdict(stage=STAGE_FUZZY, matched=False, notes=["amount out of tolerance"])

    tokens = _candidate_tokens(normalized_line)
    if not tokens:
        return MatchVerdict(stage=STAGE_FUZZY, matched=False, notes=["no UTR-like token in bank line"])

    best_score = 0.0
    best_token = ""
    for token in tokens:
        ratio = fuzz.ratio(utr, token) / 100.0
        trunc = _truncation_score(utr, token)
        score = max(ratio, trunc)
        if score > best_score:
            best_score = score
            best_token = token

    if best_score < 0.85:
        return MatchVerdict(
            stage=STAGE_FUZZY,
            matched=False,
            confidence=_conf_from_score(best_score),
            score=best_score,
            notes=[f"best UTR similarity {best_score:.2f} below threshold"],
        )

    confidence = _conf_from_score(best_score)
    matched = confidence >= AUTO_LOW
    return MatchVerdict(
        stage=STAGE_FUZZY,
        matched=matched,
        confidence=confidence,
        score=best_score,
        notes=[f"fuzzy UTR match on token {best_token} (score {best_score:.2f})"],
    )


def _conf_from_score(score: float) -> int:
    """Map a 0..1 UTR similarity to a 0-100 confidence, with amount already gated."""
    if score >= 0.97:
        return AUTO_HIGH
    if score >= 0.90:
        return AUTO_LOW
    if score >= 0.85:
        return (AUTO_LOW + REVIEW_HIGH) // 2  # borderline, ~84
    return int(score * 60)
