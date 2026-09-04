"""Data + reconciliation endpoints."""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from backend.app import schemas
from backend.app.db import get_session
from backend.app.events import broadcast
from backend.app.routers.constants import API_PREFIX, TAG_DATA
from backend.app.services import reconcile_service
from backend.app.services.llm_queue import TiebreakQueue
from backend.config import settings

router = APIRouter(prefix=API_PREFIX, tags=[TAG_DATA])

# It8: process-wide async LLM tie-break queue, bound to the real (file) DB.
# Created only when a Gemini key is configured or provider is Ollama; otherwise None.
_tiebreak_queue: TiebreakQueue | None = (
    TiebreakQueue(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model if settings.llm_provider == "gemini" else settings.ollama_model,
        provider=settings.llm_provider,
        base_url=settings.ollama_base_url,
    )
    if settings.gemini_api_key or settings.llm_provider == "ollama"
    else None
)


def get_tiebreak_queue() -> TiebreakQueue | None:
    """Return the app-wide queue (exposed for tests to inject)."""
    return _tiebreak_queue


@router.post("/generate-data", response_model=schemas.GenerateResponse)
def generate_data(seed: int | None = None, db: Session = Depends(get_session)):
    return reconcile_service.generate_data(db, seed)


@router.post("/run-reconciliation", response_model=schemas.RunResponse)
def run_reconciliation(
    seed: int | None = None,
    reload_data: bool = True,
    bg: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_session),
):
    """Run the staged pipeline deterministically (stage-5 tail lands in It8).

    The deterministic report is returned immediately; the async LLM tie-break
    tail is enqueued on the process-wide queue and drained in the background.
    """
    result = reconcile_service.run_reconciliation(
        db, seed=seed, reload_data=reload_data, tiebreak_queue=_tiebreak_queue
    )
    bg.add_task(broadcast, "reconcile_complete", {"seed": seed})
    return result


@router.get("/ai-tiebreaks")
def ai_tiebreaks_status() -> dict:
    """Queue health for the It9 dashboard: pending / processed / failed."""
    if _tiebreak_queue is None:
        return {"pending": 0, "processed": 0, "failed": 0}
    return {
        "pending": _tiebreak_queue.pending(),
        "processed": _tiebreak_queue.processed(),
        "failed": _tiebreak_queue.failed(),
    }
