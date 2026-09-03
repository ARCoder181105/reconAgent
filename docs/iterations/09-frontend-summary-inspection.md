# Iteration 09 — Frontend: Summary + Data Inspection

> Phase P2. (Depends on 07 API contract; can run alongside 08.)

## Goal

Vite + React app with the summary panel and data-inspection view, consuming the locked API contract from 07. Polls async tie-break status.

## Files

- `frontend/` — scaffold (Vite + React)
- `frontend/src/main.jsx`, `frontend/src/App.jsx`
- `frontend/src/api/client.js` — thin wrapper over the FastAPI endpoints
- `frontend/src/pages/Dashboard.jsx` — summary + data inspection
- `frontend/package.json`

## Summary Panel

- Headline numbers: match rate / review rate / exception rate / verified rate
- Per-stage breakdown (matches closed at `exact` / `fuzzy_utr` / `amount_date` / `batch_sum` / `llm_tiebreak`)
- Lightweight latency/volume counters (from the API, not a metrics server)

## Data Inspection

- Raw settlements and bank-statement tables (GET `/api/settlements`, `/api/bank-statement`) — demonstrates the "messiness" of input data.

## Async Tie-Break Indicator

- After `run-reconciliation`, show "Processing AI Tie-breaks…" while the async queue handles stage 5 edges; poll until done.

## Key Notes

- No backend in this iteration beyond the API it consumes — keep components presentational; logic stays in API.
- Match page/component naming to `conventions.md` (PascalCase components, `src/pages/`, `src/components/`, `src/api/`).

## Tests

- Build succeeds (`npm run build`).
- Component renders summary from a mocked API response.
- Poll indicator toggles on/off.

## Exit Criteria

- Dashboard loads, shows summary + raw data, reflects tie-break progress.

## Commit

`feat(web): add summary and data-inspection dashboard`
