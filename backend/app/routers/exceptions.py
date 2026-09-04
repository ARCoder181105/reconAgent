"""Exception queue + Maker-Checker workflow endpoints (event-sourced)."""
from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app import models, schemas
from backend.app.db import get_session
from backend.app.events import broadcast
from backend.app.routers.constants import API_PREFIX, TAG_EXCEPTIONS
from backend.app.services import exception_service
from backend.app.services.constants import STATUS_PENDING_APPROVAL
from backend.app.services.explain import ExplanationInput, explain_exception

router = APIRouter(prefix=f"{API_PREFIX}/exceptions", tags=[TAG_EXCEPTIONS])


# --- Helpers ---


def _parse_candidates(exc: models.Exception) -> list[dict]:
    if not exc.candidates_json:
        return []
    try:
        return json.loads(exc.candidates_json)
    except (json.JSONDecodeError, TypeError):
        return []


def _enrich_one(exc: models.Exception, bl: models.BankStatement | None) -> dict:
    """Build the ExceptionOut dict with a deterministic explanation."""
    credit_paise = None
    txn_date = None
    if bl is not None:
        if bl.credit is not None:
            credit_paise = int(round(float(bl.credit) * 100))
        txn_date = bl.txn_date or bl.value_date

    inp = ExplanationInput(
        reason_code=exc.reason_code,
        confidence=exc.confidence,
        settlement_id=exc.settlement_id,
        line_id=exc.line_id,
        candidates=_parse_candidates(exc),
        credit_paise=credit_paise,
        txn_date=txn_date,
    )
    return {
        "exception_id": exc.exception_id,
        "settlement_id": exc.settlement_id,
        "line_id": exc.line_id,
        "reason_code": exc.reason_code,
        "confidence": exc.confidence,
        "candidates_json": exc.candidates_json,
        "status": exc.status,
        "created_at": exc.created_at,
        "explanation": explain_exception(inp),
    }


def _enrich_batch(db: Session, exceptions: list[models.Exception]) -> list[dict]:
    """Enrich a list of exceptions with explanations in one batch query."""
    line_ids = {exc.line_id for exc in exceptions if exc.line_id}
    bank_lines = {}
    if line_ids:
        rows = (
            db.query(models.BankStatement)
            .filter(models.BankStatement.line_id.in_(line_ids))
            .all()
        )
        bank_lines = {bl.line_id: bl for bl in rows}
    return [_enrich_one(exc, bank_lines.get(exc.line_id)) for exc in exceptions]


# --- Endpoints ---


@router.get("", response_model=list[schemas.ExceptionOut])
def list_exceptions(status: str | None = None, reason: str | None = None, db: Session = Depends(get_session)):
    """Open exceptions with reason codes + ranked candidates + explanations."""
    q = db.query(models.Exception)
    if status:
        q = q.filter(models.Exception.status == status)
    if reason:
        q = q.filter(models.Exception.reason_code == reason)
    excs = q.order_by(models.Exception.created_at, models.Exception.exception_id).all()
    return _enrich_batch(db, excs)


@router.get("/pending-approval", response_model=list[schemas.ExceptionOut])
def pending_approval(db: Session = Depends(get_session)):
    """Maker-submitted, awaiting the checker (derived projection)."""
    excs = (
        db.query(models.Exception)
        .filter(models.Exception.status == STATUS_PENDING_APPROVAL)
        .order_by(models.Exception.created_at, models.Exception.exception_id)
        .all()
    )
    return _enrich_batch(db, excs)


@router.get("/{exception_id}/events", response_model=list[schemas.ExceptionEventOut])
def exception_events(exception_id: int, db: Session = Depends(get_session)):
    """Append-only audit trail for one exception (system of record)."""
    return exception_service.list_events(db, exception_id)


@router.post("/{exception_id}/resolve", response_model=schemas.ExceptionOut)
def resolve(
    exception_id: int,
    payload: schemas.ExceptionResolveIn,
    bg: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_session),
):
    """Maker proposes a resolution (confirm/reject/override). Never closes by itself."""
    result = exception_service.resolve(
        db, exception_id, payload.maker_id, payload.action, payload.resolution_data
    )
    bg.add_task(broadcast, "exception_changed", {"exception_id": exception_id, "action": "resolve"})
    # Enrich the returned dict with the explanation.
    bl = None
    if result.line_id:
        bl = db.get(models.BankStatement, result.line_id)
    return _enrich_one(result, bl)


@router.post("/{exception_id}/approve", response_model=schemas.ExceptionOut)
def approve(
    exception_id: int,
    payload: schemas.ExceptionApproveIn,
    bg: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_session),
):
    """Checker approves (closes) or rejects (re-opens) a maker proposal."""
    result = exception_service.approve(
        db, exception_id, payload.checker_id, payload.decision, payload.reason_text
    )
    bg.add_task(broadcast, "exception_changed", {"exception_id": exception_id, "action": "approve"})
    bl = None
    if result.line_id:
        bl = db.get(models.BankStatement, result.line_id)
    return _enrich_one(result, bl)


# --- Part 2: AI explain endpoints ---


def _get_explained(db: Session, exception_id: int) -> dict:
    """Fetch one exception enriched with its explanation. Raises 404 if missing."""
    exc = db.get(models.Exception, exception_id)
    if exc is None:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")
    bl = None
    if exc.line_id:
        bl = db.get(models.BankStatement, exc.line_id)
    return _enrich_one(exc, bl)


@router.post("/{exception_id}/explain", response_model=schemas.ExplainOut)
def explain_single(exception_id: int, db: Session = Depends(get_session)):
    """On-demand AI rephrase for one exception.

    Checks for a cached AI_EXPLAIN_GENERATED event first.  On LLM failure,
    returns the deterministic explanation with source=fallback.
    """
    from backend.app.services.constants import EVENT_AI_EXPLAIN_GENERATED
    from backend.app.services.explain import explain_with_llm

    exc = db.get(models.Exception, exception_id)
    if exc is None:
        raise HTTPException(status_code=404, detail=f"Exception {exception_id} not found")

    # Check cache.
    cached = (
        db.query(models.ExceptionEvent)
        .filter(
            models.ExceptionEvent.exception_id == exception_id,
            models.ExceptionEvent.event_type == EVENT_AI_EXPLAIN_GENERATED,
        )
        .order_by(models.ExceptionEvent.timestamp.desc())
        .first()
    )
    if cached is not None and cached.resolution_data:
        try:
            data = json.loads(cached.resolution_data)
            return schemas.ExplainOut(
                exception_id=exception_id,
                explanation=data.get("explanation", ""),
                ai_summary=data.get("ai_summary", ""),
                ai_notes=data.get("ai_notes", ""),
                source=data.get("source", "llm"),
            )
        except (json.JSONDecodeError, TypeError):
            pass

    # Build deterministic explanation.
    bl = None
    if exc.line_id:
        bl = db.get(models.BankStatement, exc.line_id)

    credit_paise = None
    txn_date = None
    if bl is not None:
        if bl.credit is not None:
            credit_paise = int(round(float(bl.credit) * 100))
        txn_date = bl.txn_date or bl.value_date

    candidates = _parse_candidates(exc)
    inp = ExplanationInput(
        reason_code=exc.reason_code,
        confidence=exc.confidence,
        settlement_id=exc.settlement_id,
        line_id=exc.line_id,
        candidates=candidates,
        credit_paise=credit_paise,
        txn_date=txn_date,
    )
    deterministic = explain_exception(inp)

    # Call LLM (graceful degradation on failure).
    from backend.config import settings
    from backend.app.services.llm_queue import _default_gen_client

    client = _default_gen_client(settings.gemini_api_key)
    ai = explain_with_llm(
        client, deterministic, exc.reason_code, candidates, exc.confidence,
        settings.gemini_model,
    )

    # Persist as event (cache).
    from datetime import datetime, timezone

    event_data = json.dumps({
        "explanation": deterministic,
        "ai_summary": ai["summary"],
        "ai_notes": ai["notes"],
        "source": ai["source"],
    })
    db.add(
        models.ExceptionEvent(
            exception_id=exception_id,
            event_type=EVENT_AI_EXPLAIN_GENERATED,
            resolution_data=event_data,
            reason_text=f"AI explain ({ai['source']}): {ai['summary'][:200]}",
            timestamp=datetime.now(timezone.utc),
        )
    )
    db.commit()

    return schemas.ExplainOut(
        exception_id=exception_id,
        explanation=deterministic,
        ai_summary=ai["summary"],
        ai_notes=ai["notes"],
        source=ai["source"],
    )


@router.post("/explain", response_model=list[schemas.ExplainOut])
def explain_bulk(payload: schemas.ExplainIn, db: Session = Depends(get_session)):
    """Bulk AI-explain for multiple exceptions (single client, one loop)."""
    from backend.app.services.constants import EVENT_AI_EXPLAIN_GENERATED
    from backend.app.services.explain import explain_with_llm
    from backend.config import settings
    from backend.app.services.llm_queue import _default_gen_client

    client = _default_gen_client(settings.gemini_api_key)
    results = []
    for eid in payload.ids:
        exc = db.get(models.Exception, eid)
        if exc is None:
            continue

        bl = None
        if exc.line_id:
            bl = db.get(models.BankStatement, exc.line_id)

        credit_paise = None
        txn_date = None
        if bl is not None:
            if bl.credit is not None:
                credit_paise = int(round(float(bl.credit) * 100))
            txn_date = bl.txn_date or bl.value_date

        candidates = _parse_candidates(exc)
        inp = ExplanationInput(
            reason_code=exc.reason_code,
            confidence=exc.confidence,
            settlement_id=exc.settlement_id,
            line_id=exc.line_id,
            candidates=candidates,
            credit_paise=credit_paise,
            txn_date=txn_date,
        )
        deterministic = explain_exception(inp)

        # Check cache.
        cached = (
            db.query(models.ExceptionEvent)
            .filter(
                models.ExceptionEvent.exception_id == eid,
                models.ExceptionEvent.event_type == EVENT_AI_EXPLAIN_GENERATED,
            )
            .order_by(models.ExceptionEvent.timestamp.desc())
            .first()
        )
        if cached is not None and cached.resolution_data:
            try:
                data = json.loads(cached.resolution_data)
                results.append(schemas.ExplainOut(
                    exception_id=eid,
                    explanation=data.get("explanation", deterministic),
                    ai_summary=data.get("ai_summary", ""),
                    ai_notes=data.get("ai_notes", ""),
                    source=data.get("source", "llm"),
                ))
                continue
            except (json.JSONDecodeError, TypeError):
                pass

        ai = explain_with_llm(
            client, deterministic, exc.reason_code, candidates, exc.confidence,
            settings.gemini_model,
        )

        from datetime import datetime, timezone

        event_data = json.dumps({
            "explanation": deterministic,
            "ai_summary": ai["summary"],
            "ai_notes": ai["notes"],
            "source": ai["source"],
        })
        db.add(
            models.ExceptionEvent(
                exception_id=eid,
                event_type=EVENT_AI_EXPLAIN_GENERATED,
                resolution_data=event_data,
                reason_text=f"AI explain ({ai['source']}): {ai['summary'][:200]}",
                timestamp=datetime.now(timezone.utc),
            )
        )

        results.append(schemas.ExplainOut(
            exception_id=eid,
            explanation=deterministic,
            ai_summary=ai["summary"],
            ai_notes=ai["notes"],
            source=ai["source"],
        ))

    db.commit()
    return results
