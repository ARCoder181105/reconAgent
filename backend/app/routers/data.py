"""Data + reconciliation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app import schemas
from backend.app.db import get_session
from backend.app.routers.constants import API_PREFIX, TAG_DATA
from backend.app.services import reconcile_service

router = APIRouter(prefix=API_PREFIX, tags=[TAG_DATA])


@router.post("/generate-data", response_model=schemas.GenerateResponse)
def generate_data(seed: int | None = None, db: Session = Depends(get_session)):
    return reconcile_service.generate_data(db, seed)


@router.post("/run-reconciliation", response_model=schemas.RunResponse)
def run_reconciliation(
    seed: int | None = None,
    reload_data: bool = True,
    db: Session = Depends(get_session),
):
    """Run the staged pipeline deterministically (stage-5 lands in It8)."""
    return reconcile_service.run_reconciliation(db, seed=seed, reload_data=reload_data)
