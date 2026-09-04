"""Maker-Checker workflow service.

Governance rules (docs/master-design.md §9, taxonomy.md):

- ``resolve`` (Maker) appends a ``MAKER_PROPOSED`` event and flips the
  projection to ``pending_approval``. The Maker proposes, never closes.
- ``approve`` (Checker) appends ``CHECKER_APPROVED`` (closes, immutable) or
  ``CHECKER_REJECTED`` (re-opens).

``Exception.status`` is only a projection cache; the event log is the system of
record. ``pending_approval`` is a *derived* view, not a stored value.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.app import models
from backend.app.services.constants import (
    EV_CHECKER_APPROVED,
    EV_CHECKER_REJECTED,
    EV_CREATED,
    EV_MAKER_PROPOSED,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _pending_maker_id(db: Session, exception_id: int) -> str | None:
    """Return the maker_id of the most recent MAKER_PROPOSED event."""
    event = (
        db.query(models.ExceptionEvent)
        .filter(
            models.ExceptionEvent.exception_id == exception_id,
            models.ExceptionEvent.event_type == EV_MAKER_PROPOSED,
        )
        .order_by(models.ExceptionEvent.timestamp.desc(), models.ExceptionEvent.event_id.desc())
        .first()
    )
    return event.maker_id if event is not None else None


def get_exception(db: Session, exception_id: int) -> models.Exception:
    exc = db.get(models.Exception, exception_id)
    if exc is None:
        raise HTTPException(status_code=404, detail=f"exception {exception_id} not found")
    return exc


def resolve(db: Session, exception_id: int, maker_id: str, action: str, resolution_data: dict | None = None):
    """Maker proposes a resolution. Only proposal with a decision string."""
    exc = get_exception(db, exception_id)
    if exc.status == "closed":
        raise HTTPException(status_code=409, detail="exception already closed by checker")

    if action not in ("confirm", "reject", "override"):
        raise HTTPException(status_code=400, detail=f"unknown action '{action}'")

    db.add(
        models.ExceptionEvent(
            exception_id=exception_id,
            event_type=EV_MAKER_PROPOSED,
            maker_id=maker_id,
            resolution_data=json.dumps(
                {
                    "action": action,
                    **(resolution_data or {}),
                    "line_id": exc.line_id,
                    "settlement_id": exc.settlement_id,
                }
            ),
            reason_text=f"maker {maker_id} proposed '{action}'",
            timestamp=_now(),
        )
    )
    exc.status = "pending_approval"
    db.commit()
    return exc


def approve(db: Session, exception_id: int, checker_id: str, decision: bool, reason_text: str | None = None):
    """Checker closes (approves) or rejects (re-opens) a maker proposal."""
    exc = get_exception(db, exception_id)
    if exc.status != "pending_approval":
        raise HTTPException(status_code=409, detail="nothing pending approval for this exception")

    maker_id = _pending_maker_id(db, exception_id)
    if maker_id is not None and maker_id == checker_id:
        raise HTTPException(
            status_code=403,
            detail="checker cannot approve their own proposal (segregation of duties)",
        )

    event_type = EV_CHECKER_APPROVED if decision else EV_CHECKER_REJECTED
    db.add(
        models.ExceptionEvent(
            exception_id=exception_id,
            event_type=event_type,
            checker_id=checker_id,
            resolution_data=json.dumps({"approved": decision}),
            reason_text=reason_text or (f"checker {checker_id} {'approved' if decision else 'rejected'}"
                                        " the maker proposal"),
            timestamp=_now(),
        )
    )
    exc.status = "closed" if decision else "open"
    db.commit()
    return exc


def list_events(db: Session, exception_id: int) -> list[models.ExceptionEvent]:
    get_exception(db, exception_id)
    return (
        db.query(models.ExceptionEvent)
        .filter(models.ExceptionEvent.exception_id == exception_id)
        .order_by(models.ExceptionEvent.timestamp, models.ExceptionEvent.event_id)
        .all()
    )
