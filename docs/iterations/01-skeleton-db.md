# Iteration 01 — Project Skeleton + DB Layer

> Phase P0. (Depends on 00.)

## Goal

Runnable backend package with the complete SQLAlchemy model layer and DB initialization, matching `master-design.md` §9 + §9.1 exactly.

## Files

- `backend/__init__.py`
- `backend/app/__init__.py`
- `backend/app/db.py` — engine, session factory, init
- `backend/app/models.py` — SQLAlchemy models
- `backend/app/schemas.py` — Pydantic schemas (start with core; expand in 07)
- `backend/config.py` — settings (DB path, seed, etc.)
- `backend/tests/conftest.py` — DB fixture (in-memory / temp)

## Model Layer (domain names, from §9)

- `Settlement` — `settlement_id` PK, `utr`, `settlement_date`, `no_of_transactions`, `gross_amount`, `fees`, `tax_gst`, `refunds_deducted`, `adjustments`, `net_amount`, `status`, `bank_account_last4`
- `BankStatement` — `line_id` PK, `txn_date`, `value_date`, `description`, `ref_no`, `debit`, `credit`, `balance`, `bank_name`
- `Match` — `match_id` PK, `settlement_id` FK, `line_id` FK, `stage` (semantic key), `confidence`, `resolved_at`
- `Exception` — `exception_id` PK, `settlement_id`, `line_id`, `reason_code`, `confidence`, `candidates_json`, `status` (projection cache: `open`/`closed`), `created_at`
- `ExceptionEvent` — `event_id` PK, `exception_id` FK, `event_type`, `maker_id`, `checker_id`, `resolution_data`, `reason_text`, `timestamp` (append-only; system of record)

## Key Notes

- **Amounts**: integer paise everywhere (mirrors schema). The noisy bank `balance` may stay `REAL`; it's unused for matching.
- **Dates**: store normalized `YYYY-MM-DD` strings (lexicographically sortable) as the design requires.
- **Event sourcing**: `Exception.status` is a projection cache, NOT the source of truth. Never update it in place for governance state — the event log holds truth. For now just define the model; the projection logic lands in 05/07.
- `db.py` init creates all tables.

## Tests

- DB init creates all 5 tables.
- Insert a `Settlement` + read it back; paise arithmetic intact.
- `ExceptionEvent` FK to `Exception` enforced.

## Exit Criteria

- `pytest` green.
- A session can init DB, insert, query.

## Commit

`feat(db): add ORM models for settlements, statements, matches, exceptions`
