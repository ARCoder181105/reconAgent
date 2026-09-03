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


def run_reconciliation(db, seed: int | None = None, reload_data: bool = True) -> dict:
    """Load CSVs, run the pipeline, persist matches + exceptions + events."""
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

    return {"report": _map_resolve(result.report)}


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
