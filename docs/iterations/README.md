# ReconAgent — Iterations

> Implementation work target. Each file is one independently-committable milestone. Work bottom-up (01 → 11); each iteration ends with tests passing + a conventional commit per the rule in `AGENTS.md`.

## How To Read This

- Files are prefixed `NN-` in dependency order.
- Every iteration lists: **Goal**, **Phase**, **Files** (new implementation names), **Key notes**, **Tests**, **Exit criteria**, **Commit message**.
- Naming convention below is locked and baked into every file. Docs (`taxonomy.md`, `master-design.md`) are updated once up front (see `00-docs-alignment.md`).
- Backend (01–08) is fully testable without the frontend. Frontend (09–10) depends on the API contract that lands in 07. 11 is docs/polish.

## Master Checklist

| # | Iteration | Phase | Status |
|---|---|---|---|
| 00 | Docs alignment (semantic naming + filenames) | — | pending |
| 01 | Skeleton + DB layer | P0 | pending |
| 02 | Data generator + hidden answer key | P0 | pending |
| 03 | Normalize + exact + fuzzy UTR matching | P0 | pending |
| 04 | Amount/date + batch-sum matching | P0/P1 | pending |
| 05 | Reconcile orchestration + exception engine + report | P0/P1 | pending |
| 06 | Scoring vs hidden answer key | P1 | pending |
| 07 | FastAPI backend + full API | P1/P2 | pending |
| 08 | Async LLM tie-break | P2 | done |
| 09 | Frontend: summary + data inspection | P2 | done |
| 10 | Exception queue + Maker-Checker + bulk resolve | P2 | pending |
| 11 | Docs finalization + demo pack | P3 | pending |

## Naming Convention (locked)

| Design / old | Implementation |
|---|---|
| Stage 0 normalize | `normalizer.py` |
| Stage 1 exact | `exact_match.py` |
| Stage 2 fuzzy UTR | `fuzzy_match.py` |
| Stage 3 amount+date | `amount_date_match.py` |
| Stage 4 batch-sum | `batch_match.py` |
| Stage 5 LLM | `llm_tiebreak.py` |
| pipeline.py | `reconcile.py` |
| `razorpay_settlements.csv` | `settlements.csv` |
| `razorpay` generator | `generate_settlements.py` / `generate_statement.py` |
| `matches.stage` values | `exact` / `fuzzy_utr` / `amount_date` / `batch_sum` / `llm_tiebreak` |

Canonical vocabulary (reason codes, event types, endpoints, ORM models) is unchanged — it is clean and locked in `taxonomy.md` / `master-design.md`.
