# ReconAgent — Ownership

> Single-owner project (the human maintainer). "Ownership" here means **work-phase ownership** across 3 clusters, not multi-person division. The one developer works the clusters in dependency order, but each cluster has a defined concern + boundaries so work stays coherent.

## Cluster A — Data Gen & Scoring

**Concern**: synthetic data + ground truth + measurement.

| Scope | Files |
|---|---|
| Settlement + bank statement generator | `data_generator/generate_settlements.py`, `generate_statement.py` |
| Ratio/seed config | `data_generator/seed_config.py` |
| Hidden answer key | `data_generator/answer_key.py` |
| Offline scoring | `scoring/score_against_answer_key.py` |

**Boundary**: must not hand `answer_key.json` to the matcher. Scoring is offline-only.

## Cluster B — Backend Matcher & API

**Concern**: matching pipeline, persistence, REST API, event sourcing.

| Scope | Files |
|---|---|
| DB + models | `app/db.py`, `app/models.py`, `app/schemas.py` |
| Pipeline stages | `app/matcher/` (normalizer, exact/fuzzy/amount_date/batch/llm, reconcile.py) |
| Exception engine + clustering | within matcher/exception engine module |
| API endpoints | `app/main.py` (generate, run, report, matches, exceptions, resolve, approve, score) |
| Async LLM tie-break | `app/matcher/llm_tiebreak.py` + queue |

**Boundary**: only Cluster B writes to SQLite; exposes the API the UI consumes.

## Cluster C — Dashboard & Maker-Checker UI

**Concern**: React frontend; user-facing exception review.

| Scope | Files |
|---|---|
| Summary panel | `src/pages/Dashboard.jsx` |
| Exception queue + Bulk Resolve | `src/pages/ExceptionQueue.jsx` |
| Pending Approval (Checker) | `src/pages/ExceptionQueue.jsx` (tab) |
| Audit trail | `src/pages/AuditTrail.jsx` |
| Data inspection | `src/pages/Dashboard.jsx` / dedicated view |

**Boundary**: reads via API; triggers maker/checker actions via API. Never touches DB directly.

## Status Per Cluster

| Cluster | Status | Owner |
|---|---|---|
| A — Data Gen & Scoring | _not started_ | human (single) |
| B — Backend Matcher & API | _not started_ | human (single) |
| C — Dashboard & Maker-Checker UI | _not started_ | human (single) |

Work order: A → B → C with overlap at phase boundaries (see `flow.md`). Statuses update in `tasks.md`.
