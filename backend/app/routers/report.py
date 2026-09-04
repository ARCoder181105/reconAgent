"""Report + matches (audit trail) endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.constants import EVENT_CHECKER_APPROVED
from backend.app import models, schemas
from backend.app.db import get_session
from backend.app.routers.constants import (
    API_PREFIX,
    AUTO_CONF_MIN,
    REVIEW_CONF_HIGH,
    REVIEW_CONF_LOW,
    TAG_REPORT,
)

router = APIRouter(prefix=API_PREFIX, tags=[TAG_REPORT])


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

    auto_matched = {m.settlement_id for m in matches if m.confidence >= AUTO_CONF_MIN}
    review = {
        m.settlement_id for m in matches
        if REVIEW_CONF_LOW <= m.confidence < REVIEW_CONF_HIGH
    }
    matched_ids = {m.settlement_id for m in matches}
    verified_ids = _verified_ids(db)

    # Per-stage confidence split so the dashboard can show which stages
    # auto-close vs which always need a human reviewer (decision D6).
    by_stage_auto: dict[str, int] = {}
    by_stage_review: dict[str, int] = {}
    for m in matches:
        bucket = by_stage_auto if m.confidence >= AUTO_CONF_MIN else by_stage_review
        bucket[m.stage] = bucket.get(m.stage, 0) + 1

    # --- Cash position (Track 04: run the books, not just count them) ---
    # Four money views of the book (paise summed, exposed as whole rupees).
    # auto/review/exceptions are mutually exclusive partitions of settlements;
    # verified is a diagonal across them (checker-closed). verified doing the
    # *same or less* than auto is intent, not a bug (decision D6).
    amounts = {s.settlement_id: s.net_amount or 0 for s in db.query(models.Settlement).all()}

    def rupees(ids: set[str]) -> float:
        return round(sum(amounts.get(sid, 0) for sid in ids) / 100, 2)

    cash = {
        "rupees_auto": rupees(auto_matched),
        "rupees_review": rupees(review),
        "rupees_exceptions": rupees(set(amounts) - matched_ids),
        "rupees_verified": rupees(verified_ids),
    }

    return {
        "total_settlements": settlements,
        "total_bank_lines": lines,
        "matched_settlements": len(matched_ids),
        "auto_matched": len(auto_matched),
        "review_queue": len(review),
        "unmatched_settlements": settlements - len(matched_ids),
        "bank_lines_matched": len({m.line_id for m in matches}),
        "bank_line_exceptions": lines - len({m.line_id for m in matches}),
        "match_rate": pct(len(auto_matched)),
        "review_rate": pct(len(review)),
        "exception_rate": pct(settlements - len(matched_ids)),
        "verified_count": len(verified_ids),
        "verified_rate": pct(len(verified_ids)),
        "by_stage": by_stage,
        "by_stage_auto": by_stage_auto,
        "by_stage_review": by_stage_review,
        "by_reason": by_reason,
        "cash": cash,
    }


def _verified_ids(db: Session) -> set[str]:
    """Settlement ids whose pairing was closed by a checker (CHECKER_APPROVED)."""
    rows = (
        db.query(models.Exception.settlement_id)
        .join(models.ExceptionEvent, models.ExceptionEvent.exception_id == models.Exception.exception_id)
        .filter(models.ExceptionEvent.event_type == EVENT_CHECKER_APPROVED)
        .all()
    )
    return {r[0] for r in rows if r[0]}


def _verified_count(db: Session) -> int:
    return len(_verified_ids(db))


@router.get("/matches", response_model=list[schemas.MatchOut])
def list_matches(stage: str | None = None, min_conf: int | None = None, db: Session = Depends(get_session)):
    q = db.query(models.Match)
    if stage:
        q = q.filter(models.Match.stage == stage)
    if min_conf is not None:
        q = q.filter(models.Match.confidence >= min_conf)
    return q.order_by(models.Match.match_id).all()
