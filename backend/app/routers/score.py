"""Eval/score endpoint — the only place the hidden answer key is consulted."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.data_generator.generator import generate_to_disk
from backend.app.data_generator.seed_config import build_config
from backend.app.db import get_session
from backend.app.matcher.reconcile import reconcile
from backend.app.routers.constants import API_PREFIX, TAG_SCORE
from backend.eval.score import score_reconciliation
from backend.app.services import reconcile_service
from backend.constants import DEFAULT_SEED

router = APIRouter(prefix=API_PREFIX, tags=[TAG_SCORE])


@router.get("/score")
def score(seed: int = DEFAULT_SEED, db: Session = Depends(get_session)):
    """Eval mode: regenerate, reconcile, and score against the hidden key."""
    from backend.config import settings

    cfg = build_config(seed=seed)
    dataset = generate_to_disk(settings.data_dir, cfg)

    settlements = reconcile_service.load_csv_rows(settings.data_dir / "settlements.csv")
    lines = reconcile_service.load_csv_rows(settings.data_dir / "bank_statement.csv")
    result = reconcile(settlements, lines)
    matches = [m.as_dict() for m in result.matches]

    answer_key = json.loads((settings.data_dir / "answer_key.json").read_text(encoding="utf-8"))
    card = score_reconciliation(answer_key, matches)

    return {
        "seed": seed,
        "report": result.report,
        "scorecard": card.as_dict(),
    }
