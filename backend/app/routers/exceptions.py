"""Exception queue + Maker-Checker workflow endpoints (event-sourced)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app import models, schemas
from backend.app.db import get_session
from backend.app.services import exception_service

router = APIRouter(prefix="/api/exceptions", tags=["exceptions"])


@router.get("", response_model=list[schemas.ExceptionOut])
def list_exceptions(status: str | None = None, reason: str | None = None, db: Session = Depends(get_session)):
    """Open exceptions with reason codes + ranked candidates."""
    q = db.query(models.Exception)
    if status:
        q = q.filter(models.Exception.status == status)
    if reason:
        q = q.filter(models.Exception.reason_code == reason)
    return q.order_by(models.Exception.created_at, models.Exception.exception_id).all()


@router.get("/pending-approval", response_model=list[schemas.ExceptionOut])
def pending_approval(db: Session = Depends(get_session)):
    """Maker-submitted, awaiting the checker (derived projection)."""
    return (
        db.query(models.Exception)
        .filter(models.Exception.status == "pending_approval")
        .order_by(models.Exception.created_at, models.Exception.exception_id)
        .all()
    )


@router.get("/{exception_id}/events", response_model=list[schemas.ExceptionEventOut])
def exception_events(exception_id: int, db: Session = Depends(get_session)):
    """Append-only audit trail for one exception (system of record)."""
    return exception_service.list_events(db, exception_id)


@router.post("/{exception_id}/resolve", response_model=schemas.ExceptionOut)
def resolve(exception_id: int, payload: schemas.ExceptionResolveIn, db: Session = Depends(get_session)):
    """Maker proposes a resolution (confirm/reject/override). Never closes by itself."""
    return exception_service.resolve(
        db, exception_id, payload.maker_id, payload.action, payload.resolution_data
    )


@router.post("/{exception_id}/approve", response_model=schemas.ExceptionOut)
def approve(exception_id: int, payload: schemas.ExceptionApproveIn, db: Session = Depends(get_session)):
    """Checker approves (closes) or rejects (re-opens) a maker proposal."""
    return exception_service.approve(db, exception_id, payload.checker_id, payload.decision, payload.reason_text)
