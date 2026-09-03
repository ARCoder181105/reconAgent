# ReconAgent — Tasks

> Active work items mapped to the P0/P1/P2 plan (`flow.md`). Statuses: `pending` / `in_progress` / `done` / `blocked`. Update statuses here as work progresses; `backlog.md` holds future/icebox items; `changelog.md` records what changed.

## Phase P0 — Demoable Core

| # | Task | Cluster | Status |
|---|---|---|---|
| P0.1 | Data generator: settlements, bank statement, seed config | A | _not started_ |
| P0.2 | Answer key generator (hidden) | A | _not started_ |
| P0.3 | DB bootstrap: db.py, models, schema DDL (incl. exception_events) | B | _not started_ |
| P0.4 | Stage 0 normalize + Stage 1 exact matcher | B | _not started_ |
| P0.5 | Stage 2 fuzzy UTR matcher (rapidfuzz) | B | _not started_ |
| P0.6 | Stage 3 amount + date matcher | B | _not started_ |
| P0.7 | Baseline exception list (JSON/console) | B | _not started_ |
| P0.8 | Headline metrics: match/review/exception rates | B | _not started_ |

## Phase P1 — Core Differentiator

| # | Task | Cluster | Status |
|---|---|---|---|
| P1.1 | Stage 4 batch-sum DP solver (bounded subset-sum) | B | _not started_ |
| P1.2 | Reason codes + ranked candidates on exceptions | B | _not started_ |
| P1.3 | Exception clustering (reason code + string heuristics) | B | _not started_ |
| P1.4 | Scoring script vs answer key (precision/recall, 3x FP) | A | _not started_ |
| P1.5 | GET /api/report + /api/score | B | _not started_ |

## Phase P2 — Polish That Wins

| # | Task | Cluster | Status |
|---|---|---|---|
| P2.1 | React dashboard: summary, queue, audit trail, inspection | C | _not started_ |
| P2.2 | Maker-Checker workflow + event-sourced log | B | _not started_ |
| P2.3 | Bulk Select & Resolve | C | _not started_ |
| P2.4 | Stage 5 async LLM tie-break (Gemini structured output) | B | _not started_ |
| P2.5 | API: resolve (maker) / approve (checker) / pending-approval | B | _not started_ |

## Current

Nothing in progress yet — build has not started. First action: P0.1 (data generator), which everything else depends on.
