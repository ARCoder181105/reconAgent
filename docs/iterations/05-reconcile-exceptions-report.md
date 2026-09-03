# Iteration 05 — Reconcile Orchestration + Exception Engine + Report

> Phase P0/P1. (Depends on 04.)

## Goal

Wire stages 1–4 into `reconcile.py`; route unresolved records through the confidence-tiering exception engine; persist matches + exceptions + `CREATED` events; output a baseline report with the headline rates.

## Files

- `backend/app/matcher/reconcile.py` — orchestrates normalize → exact → fuzzy → amount_date → batch
- `backend/app/exceptions/__init__.py`
- `backend/app/exceptions/engine.py` — confidence tiering → reason codes → candidates
- `backend/app/report.py` — baseline report (console/JSON)
- (Stage 5 stub deferred to 08; leave a clean hook)

## Behavior

**`reconcile.py`**
- Runs stages in strict order; a record only advances if earlier stages could not close it with confidence.
- Persists auto-matches to `Match` with semantic `stage` key + confidence.
- Passes the residue to the exception engine.

**Exception engine**
- Applies confidence tiers from `taxonomy.md` (auto-match ≥85; review 60–84; hard <60).
- Each exception records: `reason_code`, `stage`, `confidence`, top 1–3 candidate scores (`candidates_json`).
- Reason codes: `NO_CANDIDATE`, `MULTIPLE_CANDIDATES`, `AMOUNT_MISMATCH`, `UTR_UNRESOLVED`, `DATE_OUT_OF_WINDOW`, `BATCH_PARTITION_AMBIGUOUS`.
- Append a `CREATED` event to `exception_events` for each exception (event-sourced; status projection updated as cache).

**Report (`report.py`)**
```
match_rate     = auto_matched / total_records
review_rate    = review_queue / total_records
exception_rate = hard_exceptions / total_records
verified_rate  = records_closed / total_records    -- 0 until 07 (Maker-Checker)
```
- Always process the whole batch; never pre-filter.

## Tests

- Full batch (from 02) runs end-to-end without error.
- All "true matches" from the answer-key's easy/medium bands resolve via stages 1–2; hard cases land in review/ambiguous.
- Genuine orphans → exceptions with `NO_CANDIDATE`.
- Report rates sum correctly (match + review + exception = 1 over the batch).
- Every exception has a `CREATED` event.

## Exit Criteria

- Deterministic full-batch run with honest exception list + baseline rates (no frontend, console/JSON).

## Commit

`feat: add reconcile orchestration, exception engine, baseline report`
