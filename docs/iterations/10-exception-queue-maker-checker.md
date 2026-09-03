# Iteration 10 — Exception Queue + Maker-Checker + Bulk Resolve

> Phase P2. (Depends on 09.)

## Goal

The winning UI: an interactive exception queue with ranked candidates, the Maker-Checker approval flow, Bulk Select & Resolve, and the audit trail view.

## Files

- `frontend/src/pages/ExceptionQueue.jsx` — main queue + Pending Approval tab (Checker)
- `frontend/src/pages/AuditTrail.jsx` — every closed match, filterable by stage/confidence
- `frontend/src/components/` — row, candidates expansion, bulk bar, reason-code badge
- `frontend/src/api/client.js` — extend with resolve/approve/pending-approval

## Exception Queue

- Table: reason code, confidence, ranked candidates expandable per row.
- Actions: Confirm / Reject / Manual Override.
- **Maker** initiates → `POST /api/exceptions/{id}/resolve` → moves to `pending_approval`.
- **Checker** signs off in a **Pending Approval** tab → `POST /api/exceptions/{id}/approve` → books close.

## Bulk Select & Resolve

- Checkbox column + "Apply Rule" button → batch-process identical exceptions (e.g. 20× `NO_CANDIDATE`) with one rule/reason code.
- This is powered by the lightweight clustering (reason code + string heuristics) from `master-design.md` §7.1 — the UI surfaces cluster groups, not just isolated rows.

## Audit Trail

- Every closed match, filterable by stage and confidence — lets a reviewer spot-check auto-matches, not just exceptions.

## Key Notes

- Read the event log per exception to rebuild current state; `pending_approval` is derived, not a stored column.
- Keep components presentational; all state transitions happen through the API (07).

## Tests

- Component: select N rows → apply rule → calls resolve N times or batch endpoint.
- Maker resolve → record appears in Pending Approval; Checker approve → disappears + audit trail shows closed.
- Checker reject → moves back to open.

## Exit Criteria

- Full product loop in the UI: generate → run → review → bulk/individual resolve → approve → measure.

## Commit

`feat(web): add exception queue, maker-checker approval, bulk resolve`
