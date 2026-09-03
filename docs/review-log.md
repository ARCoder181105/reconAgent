# ReconAgent — Review Log

> Design decisions reviewed / approved by the human maintainer, with dates. Append-only (newest on top). This is the human-approval trail.

| Date | Item | Decision | Status |
|---|---|---|---|
| 2026-09-03 | Docs scope & structure | Human approved generating full requested docs set under `docs/`, moving master spec to `docs/master-design.md`, plain filenames (no numbering). | Approved |
| 2026-09-03 | Infra scope (ChromaDB, Prometheus, event sourcing, async) | Human chose **event sourcing + async only** as committed; ChromaDB + Prometheus demoted to Future Scope / stretch. | Approved |
| 2026-09-03 | Ownership model | Human confirmed single-owner project; ownership.md framed as work phases (3 clusters), not multi-person division. | Approved |
| 2026-09-03 | Maker-Checker + verified-rate metric | Recommend distinguishing engine `match_rate` from closed-books `verified_rate`; incorporated. | Noted (parts approved with docs scope) |

## Pending Human Review

Assumptions still awaiting ratification — see `assumptions.md` (A1, A2, A4, A7, A8, A9, A10, A11, A12, A13 especially).

## Rule

A decision marked Approved is binding. If you later reverse it, add a new row noting the reversal and update `decisions.md` + `changelog.md`. Never edit an old row.
