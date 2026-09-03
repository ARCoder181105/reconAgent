"""Report + matches (audit trail) endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app import models, schemas
from backend.app.db import get_session

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/report")
def report(stage: str | None = None, db: Session = Depends(get_session)):
    """Match/review/exception rates + per-stage breakdown, computed live."""
    matches = db.query(models.Match).all()
    exceptions = db.query(models.Exception).all()
    settlements = db.query(models.Settlement).count()
    lines = db.query(models.BankStatement).count()

    by_stage: dict[str, int] = {}
    for m in matches:
        by_stage[m.stage] = by_stage.get(m.stage, 0) + 1
    if stage and stage in by_stage:
        by_stage = {stage: by_stage[stage]}

    by_reason: dict[str, int] = {}
    for e in exceptions:
        by_reason[e.reason_code] = by_reason.get(e.reason_code, 0) + 1

    total = settlements or 1

    def pct(n: int) -> float:
        return round(100.0 * n / total, 2)

    auto_matched = {m.settlement_id for m in matches if m.confidence >= 85}
    review = {m.settlement_id for m in matches if 60 <= m.confidence < 85}

    return {
        "total_settlements": settlements,
        "total_bank_lines": lines,
        "matched_settlements": len({m.settlement_id for m in matches}),
        "auto_matched": len(auto_matched),
        "review_queue": len(review),
        "unmatched_settlements": settlements - len({m.settlement_id for m in matches}),
        "bank_lines_matched": len({m.line_id for m in matches}),
        "bank_line_exceptions": lines - len({m.line_id for m in matches}),
        "match_rate": pct(len(auto_matched)),
        "review_rate": pct(len(review)),
        "exception_rate": pct(settlements - len({m.settlement_id for m in matches})),
        "verified_count": _verified_count(db),
        "verified_rate": pct(_verified_count(db)),
        "by_stage": by_stage,
        "by_reason": by_reason,
    }


def _verified_count(db: Session) -> int:
    """Settlements whose pairing was closed by a checker (CHECKER_APPROVED)."""
    rows = (
        db.query(models.Exception.settlement_id)
        .join(models.ExceptionEvent, models.ExceptionEvent.exception_id == models.Exception.exception_id)
        .filter(models.ExceptionEvent.event_type == "CHECKER_APPROVED")
        .all()
    )
    return len({r[0] for r in rows if r[0]})


@router.get("/matches", response_model=list[schemas.MatchOut])
def list_matches(stage: str | None = None, min_conf: int | None = None, db: Session = Depends(get_session)):
    q = db.query(models.Match)
    if stage:
        q = q.filter(models.Match.stage == stage)
    if min_conf is not None:
        q = q.filter(models.Match.confidence >= min_conf)
    return q.order_by(models.Match.match_id).all()
