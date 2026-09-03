# Iteration 07 — FastAPI Backend + Full API

> Phase P1/P2. (Depends on 06.)

## Goal

Expose the whole product through FastAPI: data generation, reconciliation run, maker/checker exception workflow (event-sourced), measurement, and raw data inspection.

## Files

- `backend/app/main.py` — app + router mounting
- `backend/app/routers/` — split by concern: `data.py`, `run.py`, `report.py`, `matches.py`, `exceptions.py`, `inspector.py`, `score.py`
- `backend/app/schemas.py` — expanded Pydantic DTOs (also reused by frontend later)
- `backend/app/services/report_service.py` (thin; may just call existing modules)
- `backend/app/test_main.py` — httpx TestClient integration

## Endpoints (from `master-design.md` §10)

| Method | Endpoint | Notes |
|---|---|---|
| POST | `/api/generate-data` | seed both CSVs + hidden answer key |
| POST | `/api/run-reconciliation` | run staged pipeline; returns deterministic results; async stage-5 later |
| GET | `/api/report` | match/review/exception/verified rates + per-stage |
| GET | `/api/matches` | audit trail, filterable by stage/confidence |
| GET | `/api/exceptions` | open exceptions with reason codes + candidates |
| POST | `/api/exceptions/{id}/resolve` | **maker** proposes → `MAKER_PROPOSED` event |
| POST | `/api/exceptions/{id}/approve` | **checker** approves/rejects → `CHECKER_APPROVED` / `CHECKER_REJECTED` |
| GET | `/api/exceptions/pending-approval` | maker-submitted, awaiting checker |
| GET | `/api/settlements` | data inspection |
| GET | `/api/bank-statement` | data inspection |
| GET | `/api/score` | eval mode only — runs scoring (06) |

## Key Notes

- **Event sourcing**: resolve appends `MAKER_PROPOSED`; approve appends `CHECKER_APPROVED`/`CHECKER_REJECTED`. Exception status is a projection rebuilt from events (cache row updated, event log is source of truth). Maker can propose; only Checker closes books.
- No auth (prototype) — but keep `maker_id`/`checker_id` fields so the workflow is real.
- `run-reconciliation` returns deterministic results synchronously; stage-5 async lands in 08.
- Lock the API contract here — the frontend (09–10) builds against it.

## Tests

- httpx TestClient full happy path: generate → run → fetch exceptions → resolve (maker) → approve (checker) → report reflects `verified_rate`.
- Pending-approval list shows maker-submitted before approval, empty after.
- Checker reject path appends event + re-opens exception.
- `/api/score` runs offline scoring.

## Exit Criteria

- Every endpoint works end-to-end.
- Maker-Checker + event-sourced audit trail exercised through the API.

## Commit

`feat(api): add FastAPI backend with maker-checker and measurement endpoints`
