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

from backend.constants import STAGE_FUZZY_UTR
from backend.app.matcher.constants import (
    AUTO_HIGH,
    AUTO_LOW,
    DEFAULT_AMOUNT_TOLERANCE_PAISE,
    FUZZY_AUTO_HIGH_SCORE,
    FUZZY_AUTO_LOW_SCORE,
    FUZZY_DOMINANT_MIN_RATIO,
    FUZZY_DOMINANT_MIN_SCORE,
    FUZZY_MIN_SCORE,
    REVIEW_HIGH,
    UTR_TOKEN_RE,
    MatchVerdict,
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


def fuzzy_match(normalized_settlement: dict, normalized_line: dict, tolerance_paise: int = DEFAULT_AMOUNT_TOLERANCE_PAISE) -> MatchVerdict:
    """Judge a fuzzy UTR match for the settlement against the bank line."""
    utr = normalized_settlement.get("utr", "")
    if not utr:
        return MatchVerdict(stage=STAGE_FUZZY_UTR, matched=False, notes=["settlement has no UTR"])

    if not amount_close(normalized_settlement["net_amount"], normalized_line.get("credit_paise") or 0, tolerance_paise):
        return MatchVerdict(stage=STAGE_FUZZY_UTR, matched=False, notes=["amount out of tolerance"])

    tokens = _candidate_tokens(normalized_line)
    if not tokens:
        return MatchVerdict(stage=STAGE_FUZZY_UTR, matched=False, notes=["no UTR-like token in bank line"])

    best_score = 0.0
    best_token = ""
    for token in tokens:
        ratio = fuzz.ratio(utr, token) / 100.0
        trunc = _truncation_score(utr, token)
        score = max(ratio, trunc)
        if score > best_score:
            best_score = score
            best_token = token

    if best_score < FUZZY_MIN_SCORE:
        return MatchVerdict(
            stage=STAGE_FUZZY_UTR,
            matched=False,
            confidence=_conf_from_score(best_score),
            score=best_score,
            notes=[f"best UTR similarity {best_score:.2f} below threshold"],
        )

    confidence = _conf_from_score(best_score)
    matched = confidence >= AUTO_LOW
    return MatchVerdict(
        stage=STAGE_FUZZY_UTR,
        matched=matched,
        confidence=confidence,
        score=best_score,
        notes=[f"fuzzy UTR match on token {best_token} (score {best_score:.2f})"],
    )


def _conf_from_score(score: float) -> int:
    """Map a 0..1 UTR similarity to a 0-100 confidence, with amount already gated."""
    if score >= FUZZY_AUTO_HIGH_SCORE:
        return AUTO_HIGH
    if score >= FUZZY_AUTO_LOW_SCORE:
        return AUTO_LOW
    if score >= FUZZY_MIN_SCORE:
        return (AUTO_LOW + REVIEW_HIGH) // 2  # borderline, ~84
    return int(score * 60)


def dominant_utr_match(
    normalized_line: dict,
    candidate_settlements: list[dict],
) -> tuple[str, MatchVerdict] | None:
    """Recover the single clearly-dominant UTR candidate that normal stages missed.

    Fires only when NO settlement reached the normal fuzzy accept gate but one
    record bests the field by a wide margin (clear UTR separation). The amount
    must already be in tolerance for the candidate to count. This is a low-risk,
    explainable tie-break that keeps ``FUZZY_MIN_SCORE`` conservative — it can
    pick the *intended* UTR even when the amount+date stage is deliberately
    ambiguous (near-identical amounts), because the UTR is the stronger signal.

    Returns ``(settlement_id, matched_verdict)``, or ``None`` when guards fail.
    """
    token_source: dict[str, float] = {}
    for s in candidate_settlements:
        utr = s.get("utr", "")
        if not utr:
            continue
        # Amount must be plausible (within tolerance) for the candidate to count.
        if not amount_close(s["net_amount"], normalized_line.get("credit_paise") or 0):
            continue
        tokens = _candidate_tokens(normalized_line)
        best = 0.0
        for tok in tokens:
            best = max(best, fuzz.ratio(utr, tok) / 100.0, _truncation_score(utr, tok))
        if best > 0:
            token_source[s["settlement_id"]] = best

    if not token_source:
        return None

    best_id = max(token_source, key=token_source.get)
    best = token_source[best_id]
    second = sorted(token_source.values())[-2] if len(token_source) >= 2 else 0.0

    # Conservative gates: near-threshold best + clear margin over every rival.
    if best < FUZZY_DOMINANT_MIN_SCORE:
        return None
    if best < FUZZY_DOMINANT_MIN_RATIO * second:
        return None

    verdict = MatchVerdict(
        stage=STAGE_FUZZY_UTR,
        matched=True,
        confidence=REVIEW_HIGH,
        score=best,
        notes=[
            f"dominant fuzzy UTR candidate {best_id} (score {best:.2f}, "
            f"next {second:.2f}, ratio {best / second if second else float('inf'):.2f})"
        ],
    )
    return best_id, verdict
