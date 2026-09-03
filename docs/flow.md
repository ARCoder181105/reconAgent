# ReconAgent — Implementation Flow

> Build sequence driven by the P0/P1/P2 plan in `master-design.md` §14. Single-owner project; this is the order of work, not a timeline.

## Principle

Build P0 end-to-end before touching P1. A working, honestly-scored full pipeline on the simplest cases beats a half-built version of every feature.

```
P0 ──> P1 ──> P2 ──> (P3 stretch)
```

## Phase P0 — Demoable Core (must exist for any demo)

1. Data generator: `generate_settlements.py`, `generate_statement.py`, `seed_config.py`, `answer_key_generator.py`
2. DB bootstrap: `db.py`, `models.py`, schema DDL (settlements, bank_statement, matches, exceptions, exception_events)
3. Stages 1–3 of matching engine (normalize, exact, fuzzy UTR, amount/date)
4. Baseline exception list as JSON/console
5. Headline numbers: match rate / review rate / exception rate

**Exit criteria:** full batch runs end-to-end, honest exception list printed, no frontend.

## Phase P1 — Core Differentiator

6. Stage 4 batch-sum DP solver (bounded subset-sum)
7. Reason codes + ranked candidates on every exception
8. Exception clustering via reason code + string heuristics (lightweight, no ChromaDB)
9. Scoring script against hidden answer key (precision/recall, weighted 3x on FP)
10. `GET /api/report`, `GET /api/score`

**Exit criteria:** measured accuracy available; per-stage breakdown meaningful.

## Phase P2 — Polish That Wins

11. React dashboard (summary, exception queue, audit trail, data inspection)
12. Maker-Checker workflow: maker proposes, checker approves, event-sourced log
13. Bulk Select & Resolve
14. Stage 5 async LLM tie-break (Gemini, structured output)
15. API: `/api/exceptions/{id}/resolve` (maker), `/api/exceptions/{id}/approve` (checker), `pending-approval` queue

**Exit criteria:** full product loop — generate → run → review → approve → measure — in the UI.

## Phase P3 — Stretch (only if time remains)

- Real-data texture layer (narration templates, realistic amount distributions)
- Per-stage breakdown visualization polish
- Multi-bank-account scenario

---

## Dependencies

- P0 must precede all (data gen feeds everything)
- Stage order inside pipeline is mandatory (each stage feeds the next)
- Scoring depends on data gen producing `answer_key.json`
- Frontend depends on a stable API contract (lock endpoints before building UI)
- Async LLM depends on Stages 1–4 existing (it only handles leftovers)

## Current Status

Track in `tasks.md` / `backlog.md` / `changelog.md`. Progress lives there, not here.
