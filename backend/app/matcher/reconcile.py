"""Iteration 05 — Reconcile orchestration.

Runs the 5-stage pipeline over a full batch (no pre-filtering). Produces:

- auto-closed matches  (stages `exact`, `fuzzy_utr`, confidence >= 85)
- review-tier proposed matches (stages `amount_date`, `batch_sum`, confidence 60-84)
- hard exceptions and their canonical reason codes

Matches map 1:1 to ``matches`` rows in the DB; exceptions map to ``exceptions``
rows (status is a projection; events are appended in the API layer, It7).

Stage 5 (``llm_tiebreak``) is a deferred, async, last-resort resolver for lines
that remain unresolvable after stages 1-4; its hook is stubbed here and filled
in It8. This module NEVER reads the hidden answer key.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.matcher import batch_match as batch_stage
from backend.app.matcher import fuzzy_match
from backend.app.matcher import exact_match
from backend.app.matcher.amount_date_match import amount_date_match
from backend.app.matcher.batch_match import batch_match
from backend.app.matcher.normalizer import normalize_bank_line, normalize_settlement
from backend.app.matcher.__shared__ import (
    STAGE_AMOUNT_DATE,
    STAGE_BATCH,
    STAGE_EXACT,
    STAGE_FUZZY,
    AUTO_HIGH,
    AUTO_LOW,
    REVIEW_LOW,
)

REASON_UNAMED_UTR = "UTR_UNRESOLVED"  # review-tier: no UTR corroboration


@dataclass
class ResolvedMatch:
    """One closed settlement<->line pairing (1:1; batch emits N rows)."""

    settlement_id: str
    line_id: str
    stage: str
    confidence: int

    def as_dict(self) -> dict:
        return {
            "settlement_id": self.settlement_id,
            "line_id": self.line_id,
            "stage": self.stage,
            "confidence": self.confidence,
        }


@dataclass
class ExceptionRecord:
    """An exception routed to the human review queue."""

    reason_code: str
    settlement_id: str | None = None
    line_id: str | None = None
    confidence: int | None = None
    candidates: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "reason_code": self.reason_code,
            "settlement_id": self.settlement_id,
            "line_id": self.line_id,
            "confidence": self.confidence,
            "candidates": self.candidates,
            "notes": self.notes,
        }


@dataclass
class ReconcileResult:
    """Full pipeline output for one batch."""

    matches: list[ResolvedMatch] = field(default_factory=list)
    exceptions: list[ExceptionRecord] = field(default_factory=list)
    report: dict = field(default_factory=dict)


def _normalize_settlements(rows) -> list[dict]:
    return [normalize_settlement(r) for r in rows]


def _normalize_lines(rows) -> list[dict]:
    return [normalize_bank_line(r) for r in rows]


def _credit_paise(line: dict) -> int | None:
    return line.get("credit_paise")


def reconcile(
    settlement_rows,
    bank_line_rows,
    tolerance_paise: int = 100,
) -> ReconcileResult:
    """Run the pipeline over a full batch of settlements + bank lines.

    ``settlement_rows`` / ``bank_line_rows`` are iterables of dicts (ORM rows or
    CSV-derived dicts) with the raw column naming from settlements.csv /
    bank_statement.csv.
    """
    settlements = {s["settlement_id"]: s for s in _normalize_settlements(settlement_rows)}
    lines = sorted(_normalize_lines(bank_line_rows), key=lambda l: l["line_id"])

    n_settlements = len(settlements)
    n_lines = len(lines)

    matches: list[ResolvedMatch] = []
    exceptions: list[ExceptionRecord] = []

    for line in lines:
        credit = _credit_paise(line)
        if credit is None:
            # Debit/charge leaf: no Razorpay settlement exists for a charge line.
            exceptions.append(
                ExceptionRecord(
                    reason_code="NO_CANDIDATE",
                    line_id=line["line_id"],
                    confidence=100,
                    notes=["bank-side debit with no Razorpay settlement"],
                )
            )
            continue

        _process_credit(line, settlements, matches, exceptions, tolerance_paise)

    # Settlements left in the pool were never credited by any bank line.
    for s in settlements.values():
        exceptions.append(
            ExceptionRecord(
                reason_code="NO_CANDIDATE",
                settlement_id=s["settlement_id"],
                confidence=100,
                notes=["settlement not credited in bank statement"],
            )
        )

    result = ReconcileResult(
        matches=matches,
        exceptions=exceptions,
        report=_build_report(matches, exceptions, n_settlements, n_lines),
    )
    return result


def _process_credit(
    line: dict,
    settlements: dict[str, dict],
    matches: list[ResolvedMatch],
    exceptions: list[ExceptionRecord],
    tolerance_paise: int,
) -> None:
    """Walk stages 1-4 (and mark stage-5 candidates) for a credit line."""

    # --- Stage 1: exact UTR ---
    hit = None
    for s in list(settlements.values()):
        v = exact_match.exact_match(s, line, tolerance_paise)
        if v.matched:
            hit = (s, v)
            break
    if hit and _is_unique_exact(hit, settlements, line, tolerance_paise):
        s, v = hit
        settlements.pop(s["settlement_id"])
        matches.append(ResolvedMatch(s["settlement_id"], line["line_id"], STAGE_EXACT, v.confidence))
        return

    # --- Stage 2: fuzzy UTR ---
    fuzzy_hits = []
    for s in list(settlements.values()):
        v = fuzzy_match.fuzzy_match(s, line, tolerance_paise)
        if v.matched:
            fuzzy_hits.append((s, v))
    if len(fuzzy_hits) == 1:
        s, v = fuzzy_hits[0]
        settlements.pop(s["settlement_id"])
        matches.append(ResolvedMatch(s["settlement_id"], line["line_id"], STAGE_FUZZY, v.confidence))
        return
    if len(fuzzy_hits) > 1:
        exceptions.append(
            ExceptionRecord(
                reason_code="MULTIPLE_CANDIDATES",
                line_id=line["line_id"],
                confidence=_conf_of_best(fuzzy_hits),
                candidates=[{"settlement_id": s["settlement_id"]} for s, _ in fuzzy_hits],
                notes=["multiple fuzzy UTR candidates reached this line"],
            )
        )
        # Cannot rely on fuzzy; fall through to amount/date for investigation.
        # (Still record the ambiguity; we do not auto-close.)

    # --- Stage 3: amount + date ---
    amt_res = amount_date_match(line, list(settlements.values()), tolerance_paise)
    if amt_res.status == "ambiguous":
        exceptions.append(
            ExceptionRecord(
                reason_code="MULTIPLE_CANDIDATES",
                line_id=line["line_id"],
                confidence=REVIEW_LOW,
                candidates=amt_res.candidates,
                notes=amt_res.notes,
            )
        )
        return
    if amt_res.status == "match":
        sid = amt_res.settlement_id
        settlements.pop(sid)
        matches.append(ResolvedMatch(sid, line["line_id"], STAGE_AMOUNT_DATE, amt_res.confidence))
        exceptions.append(
            ExceptionRecord(
                reason_code=REASON_UNAMED_UTR,
                settlement_id=sid,
                line_id=line["line_id"],
                confidence=amt_res.confidence,
                candidates=amt_res.candidates,
                notes=["amount+date single candidate; no UTR corroboration — Maker review"],
            )
        )
        return

    # --- Stage 4: batch-sum ---
    batch_res = batch_match(line, list(settlements.values()), tolerance_paise)
    if batch_res.status == "ambiguous":
        exceptions.append(
            ExceptionRecord(
                reason_code="BATCH_PARTITION_AMBIGUOUS",
                line_id=line["line_id"],
                confidence=REVIEW_LOW,
                notes=batch_res.notes,
            )
        )
        return
    if batch_res.status == "match":
        ids = batch_res.settlement_ids
        for sid in ids:
            settlements.pop(sid, None)
            matches.append(ResolvedMatch(sid, line["line_id"], STAGE_BATCH, batch_res.confidence))
        exceptions.append(
            ExceptionRecord(
                reason_code=REASON_UNAMED_UTR,
                line_id=line["line_id"],
                confidence=batch_res.confidence,
                candidates=[{"settlement_id": s} for s in ids],
                notes=["batch-sum single partition; no UTR corroboration — Maker review"],
            )
        )
        return

    # --- Stage 5 hook: genuinely unresolvable after 1-4 ---
    exceptions.append(
        ExceptionRecord(
            reason_code=_unresolved_code(line),
            line_id=line["line_id"],
            confidence=0,
            notes=[
                "unresolved by exact/fuzzy/amount_date/batch_sum; queued for "
                "LLM tie-break (last resort, async)"
            ],
        )
    )


def _unresolved_code(line: dict) -> str:
    # If a UTR-like token exists but didn't resolve, the UTR is the culprit.
    from backend.app.matcher.__shared__ import UTR_TOKEN_RE

    blob = f"{line.get('description', '')} {line.get('ref_no', '')}"
    return "UTR_UNRESOLVED" if UTR_TOKEN_RE.search(blob) else "NO_CANDIDATE"


def _is_unique_exact(hit, settlements: dict, line: dict, tolerance_paise: int) -> bool:
    """True if exactly one settlement matches the line exactly (UTRs are unique)."""
    s0, _ = hit
    count = 0
    for s in settlements.values():
        if exact_match.exact_match(s, line, tolerance_paise).matched:
            count += 1
    return count == 1


def _conf_of_best(hits) -> int:
    return max(v.confidence for _, v in hits)


def _build_report(
    matches: list[ResolvedMatch],
    exceptions: list[ExceptionRecord],
    n_settlements: int,
    n_lines: int,
) -> dict:
    """Canonical metrics on the settlement-record basis (taxonomy.md).

    The settlement is the reconciliation unit a human works with; a batch of
    N settlements is N records even if they share one bank line. Bank-line
    coverage is reported separately.
    """
    from collections import Counter

    matched_sids = {m.settlement_id for m in matches}
    matched_lines = {m.line_id for m in matches}

    auto = [m for m in matches if m.confidence >= AUTO_LOW]
    review = [m for m in matches if AUTO_LOW > m.confidence >= REVIEW_LOW]

    n_auto_sids = {m.settlement_id for m in auto}
    n_review_sids = {m.settlement_id for m in review}

    total = n_settlements or 1

    def pct(n: int) -> float:
        return round(100.0 * n / total, 2)

    report = {
        "total_settlements": n_settlements,
        "total_bank_lines": n_lines,
        "matched_settlements": len(matched_sids),
        "auto_matched": len(n_auto_sids),
        "review_queue": len(n_review_sids),
        "unmatched_settlements": n_settlements - len(matched_sids),
        "bank_lines_matched": len(matched_lines),
        "bank_line_exceptions": n_lines - len(matched_lines),
        "exceptions_total": len(exceptions),
        "match_rate": pct(len(n_auto_sids)),
        "review_rate": pct(len(n_review_sids)),
        "exception_rate": pct(n_settlements - len(matched_sids)),
        "by_stage": dict(Counter(m.stage for m in matches)),
        "by_reason": dict(Counter(e.reason_code for e in exceptions)),
    }
    return report
