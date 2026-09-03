"""Reconciliation service: load data, run the pipeline, persist results.

Persistence follows the DB contract in ``models.py``:

- ``settlements`` / ``bank_statement``: raw records as loaded from CSV.
- ``matches``: closed pairings from the reconcile engine.
- ``exceptions``: every exception routed to human review, each seeded with a
  ``CREATED`` event; ``status`` is a projection cache whose source of truth is
  the ``exception_events`` log.
"""
from __future__ import annotations

import json

import pandas as pd

from backend.app import models
from backend.app.data_generator.generator import generate_to_disk
from backend.app.data_generator.seed_config import build_config
from backend.app.matcher.reconcile import reconcile
from backend.app.services.llm_queue import TiebreakQueue, TiebreakTask
from backend.constants import (
    REASON_NO_CANDIDATE,
    REASON_UTR_UNRESOLVED,
)

# Stage-5 candidates: reasons that represent GENUINELY unresolved credit lines
# (a real bank line with no deterministic match), eligible for the LLM tail.
_TIEBREAK_REASONS = (REASON_UTR_UNRESOLVED, REASON_NO_CANDIDATE)


def load_csv_rows(path) -> list[dict]:
    df = pd.read_csv(path)
    return df.to_dict("records")


def _map_resolve(report: dict) -> dict:
    """Convert the reconcile report into the API-facing shape."""
    return {
        "total_settlements": report["total_settlements"],
        "total_bank_lines": report["total_bank_lines"],
        "matched_settlements": report["matched_settlements"],
        "auto_matched": report["auto_matched"],
        "review_queue": report["review_queue"],
        "unmatched_settlements": report["unmatched_settlements"],
        "bank_lines_matched": report["bank_lines_matched"],
        "bank_line_exceptions": report["bank_line_exceptions"],
        "match_rate": report["match_rate"],
        "review_rate": report["review_rate"],
        "exception_rate": report["exception_rate"],
        "by_stage": report["by_stage"],
        "by_reason": report["by_reason"],
    }


def _clear(db) -> None:
    """Idempotent reset: wipe prior reconcile artifacts + raw data."""
    db.query(models.ExceptionEvent).delete()
    db.query(models.Exception).delete()
    db.query(models.Match).delete()
    db.query(models.BankStatement).delete()
    db.query(models.Settlement).delete()


def generate_data(db, seed: int | None = None) -> dict:
    """(Re)generate synthetic data to disk and persist the raw records."""
    cfg = build_config(seed=seed) if seed else build_config()
    from backend.config import settings

    dataset = generate_to_disk(settings.data_dir, cfg)

    _clear(db)
    db.bulk_insert_mappings(models.Settlement, _load_settlements(dataset))
    db.bulk_insert_mappings(models.BankStatement, _load_lines(dataset))
    db.commit()

    return {
        "seed": cfg.seed,
        "settlements": len(dataset.scenarios),
        "bank_lines": len(dataset.lines),
    }


def _load_settlements(dataset) -> list[dict]:
    from dataclasses import asdict

    rows = []
    for s in dataset.scenarios:
        d = asdict(s)
        rows.append(
            {
                "settlement_id": d["settlement_id"],
                "utr": d["utr"],
                "settlement_date": d["settlement_date"],
                "no_of_transactions": d["no_of_transactions"],
                "gross_amount": d["gross_amount"],
                "fees": d["fees"],
                "tax_gst": d["tax_gst"],
                "refunds_deducted": d["refunds_deducted"],
                "adjustments": d["adjustments"],
                "net_amount": d["net_amount"],
                "status": d["status"],
                "bank_account_last4": d["bank_account_last4"],
            }
        )
    return rows


def _load_lines(dataset) -> list[dict]:
    rows = []
    for b in dataset.lines:
        rows.append(
            {
                "line_id": b.line_id,
                "txn_date": b.txn_date,
                "value_date": b.value_date,
                "description": b.description,
                "ref_no": b.ref_no,
                "debit": b.debit,
                "credit": b.credit,
                "balance": b.balance,
                "bank_name": b.bank_name,
            }
        )
    return rows


def run_reconciliation(
    db,
    seed: int | None = None,
    reload_data: bool = True,
    tiebreak_queue=None,
) -> dict:
    """Load CSVs, run the pipeline, persist matches + exceptions + events.

    ``tiebreak_queue`` is an optional ``TiebreakQueue`` for the async LLM
    Stage 5 tail.  When supplied, eligible stage-5 exception records are
    enqueued and the background worker is started.  In tests the queue is
    ``None`` so no background thread is spawned.
    """
    from backend.config import settings

    if reload_data:
        generate_data(db, seed)

    settlements = load_csv_rows(settings.data_dir / "settlements.csv")
    lines = load_csv_rows(settings.data_dir / "bank_statement.csv")

    result = reconcile(settlements, lines)

    _clear(db)
    db.bulk_insert_mappings(models.Settlement, settlements)
    db.bulk_insert_mappings(models.BankStatement, lines)

    for m in result.matches:
        db.add(
            models.Match(
                settlement_id=m.settlement_id,
                line_id=m.line_id,
                stage=m.stage,
                confidence=m.confidence,
            )
        )

    _persist_exceptions(db, result.exceptions)
    db.commit()

    # --- It8: async LLM tie-break tail (last resort, background only) ---
    if tiebreak_queue is not None:
        enqueue_tiebreaks(db, result.exceptions, tiebreak_queue)
        tiebreak_queue.start()

    return {"report": _map_resolve(result.report)}


def enqueue_tiebreaks(db, exception_records, queue) -> int:
    """Map stage-5 eligible exception records to ``TiebreakTask`` objects.

    Returns the number of tasks enqueued.
    """
    from math import isfinite

    enqueued = 0
    for e in exception_records:
        if e.reason_code not in _TIEBREAK_REASONS:
            continue
        if not e.line_id:
            continue
        exc_rows = (
            db.query(models.Exception)
            .filter(
                models.Exception.line_id == e.line_id,
                models.Exception.reason_code.in_(_TIEBREAK_REASONS),
            )
            .all()
        )
        if not exc_rows:
            continue
        exc_id = exc_rows[0].exception_id

        # Pull the persisted raw bank line for LLM context (credit rupees -> paise).
        line = {"line_id": e.line_id}
        bl = db.get(models.BankStatement, e.line_id)
        if bl is not None:
            line = {
                "line_id": bl.line_id,
                "description": bl.description or "",
                "ref_no": bl.ref_no or "",
                "txn_date": bl.txn_date or bl.value_date or "",
                "value_date": bl.value_date or "",
            }
            credit = bl.credit
            if isinstance(credit, (int, float)) and isfinite(credit):
                line["credit_paise"] = int(round(credit * 100))

        queue.enqueue(
            TiebreakTask(
                exception_id=exc_id,
                line=line,
                candidates=e.candidates or [],
                settlement_id=e.settlement_id,
                reason_code=e.reason_code,
            )
        )
        enqueued += 1
    return enqueued


def _persist_exceptions(db, exception_records) -> None:
    """Insert exception rows + seed each with a CREATED event."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    for e in exception_records:
        exc = models.Exception(
            settlement_id=e.settlement_id,
            line_id=e.line_id,
            reason_code=e.reason_code,
            confidence=e.confidence,
            candidates_json=json.dumps(e.candidates) if e.candidates else None,
            status="open",
        )
        db.add(exc)
        db.flush()
        db.add(
            models.ExceptionEvent(
                exception_id=exc.exception_id,
                event_type="CREATED",
                resolution_data=None,
                reason_text="exception entered the queue",
                timestamp=now,
            )
        )
