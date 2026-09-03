"""Raw data inspection endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app import models, schemas
from backend.app.db import get_session

router = APIRouter(prefix="/api", tags=["inspector"])


@router.get("/settlements", response_model=list[schemas.SettlementOut])
def list_settlements(limit: int = 100, offset: int = 0, db: Session = Depends(get_session)):
    return (
        db.query(models.Settlement)
        .order_by(models.Settlement.settlement_id)
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.get("/bank-statement", response_model=list[schemas.BankStatementOut])
def list_bank_statement(limit: int = 100, offset: int = 0, db: Session = Depends(get_session)):
    return (
        db.query(models.BankStatement)
        .order_by(models.BankStatement.line_id)
        .limit(limit)
        .offset(offset)
        .all()
    )
