# ReconAgent

**Multi-Source Fuzzy Reconciliation Engine** — Razorpay Buildathon, Track 04 (AI Finance Controller).

ReconAgent matches a Razorpay-style settlement report against messy bank statement data across a 50+ record batch, reports measured accuracy, and surfaces an honest exception queue with a Maker‑Checker workflow. It is a 5‑stage deterministic pipeline (exact → fuzzy UTR → amount+date → batch‑sum → async LLM tie‑break) with an event‑sourced exception log.

> This is the build repo. The authoritative design, decisions, constraints and taxonomy live in [`docs/`](docs/) — see [`docs/sources-of-truth.md`](docs/sources-of-truth.md) for precedence. Code lives in `backend/` (React frontend lands in Iterations 9–11).

---

## Status

- **Iterations 0–8 complete & committed**: data generator, matcher (exact / fuzzy UTR / amount+date / batch‑sum), reconcile + exception engine, offline scoring with 3× false‑positive penalty, FastAPI backend, and the Stage 5 async LLM tie‑break with graceful fallback.
- **Accuracy tuning (It9 pre-dashboard)**: recovered the two deterministic miss sources — a wider batch date window and a dominant‑UTR tie‑break — lifting seed‑42 eval to **48/48, precision 1.0, recall 1.0, F1 1.0, penalized 1.0** with **0 false positives** (recall +6.25 to +8.33pp across seeds 42/43/44/45/7/123).
- **Next**: pause for review, then Iterations 9–11 (React dashboard).

---

## Features

- **5‑stage pipeline**: `exact` → `fuzzy_utr` (rapidfuzz) → `amount_date` → `batch_sum` (bounded subset‑sum) → `llm_tiebreak`. INR amounts handled as integer paise.
- **Honest exceptions**: canonical reason codes (`docs/taxonomy.md`), ranked candidates, review band (60–84) vs auto‑close (≥85).
- **Maker‑Checker + event sourcing**: Maker proposes, only a Checker closes. Exception `status` is a projection cache over an append‑only `exception_events` log — never updated in place.
- **LLM = last resort**: Stage 5 runs async in a background queue, uses Gemini structured output with strict JSON, can lift confidence into the review band (max 84) but **never** auto‑closes an exception, and degrades gracefully to a deterministic fallback on any failure.
- **Hidden answer key**: generated into `backend/data/` for scoring only; never reaches matcher scope and is gitignored.
- **Measured accuracy**: offline scoring with a 3× false‑positive penalty.

---

## Getting started

Requires **Python 3.12.3** (pinned in `.python-version`). Node/React tooling arrives with the frontend (It9).

```bash
# 1. Create the virtualenv and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure the environment (LLM key is optional; only needed for Stage 5)
cp .env.example .env        # then fill in GEMINI_API_KEY if you want the LLM tie-break

# 3. Run the API
uvicorn backend.app.main:app --reload     # or: make dev
```

### CLI / Makefile targets

```bash
make install   # install requirements into .venv
make test      # run backend/tests
make test-v    # verbose test run
make gen       # generate synthetic data (settlements.csv, bank_statement.csv, answer_key.json)
make score     # offline scoring vs hidden answer key (3x fp penalty)
make dev       # uvicorn backend.app.main:app --reload
make data      # make test + make score
make help      # list all targets
```

---

## API (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/generate-data` | Regenerate synthetic data from a seed |
| POST | `/api/run-reconciliation` | Run the pipeline deterministically (enqueues async LLM tail) |
| GET | `/api/report` | Headline metrics + verified count |
| GET | `/api/score` | Precision / recall / F1 / penalized vs answer key |
| GET | `/api/settlements` · `/api/bank-statement` · `/api/matches` | Inspection |
| GET | `/api/exceptions` · `/api/exceptions/pending-approval` | Exception queue |
| POST | `/api/exceptions/{id}/resolve` | Maker proposes (never closes) |
| POST | `/api/exceptions/{id}/approve` | Checker approves/rejects (closes) |
| GET | `/api/ai-tiebreaks` | Async LLM queue health (pending / processed / failed) |
| GET | `/health` | Liveness |

Docs are auto‑generated at `/docs` once the server is running.

---

## Architecture

```
backend/
  app/
    data_generator/     # synthetic data + hidden answer key
    matcher/            # normalize, exact, fuzzy_utr, amount_date, batch_sum,
                        #   reconcile (orchestration), llm_tiebreak (stage 5)
    services/           # reconcile_service + llm_queue (async background)
    routers/            # data, report, exceptions, inspector, score
    db.py  models.py  schemas.py
  eval/                 # offline scoring vs answer key
  tests/                # pytest suite
  config.py  constants.py
docs/                   # design + domain source of truth
```

The production data flow: `run-reconciliation` runs stages 1–4 synchronously and returns the deterministic report immediately; eligible unresolved lines are enqueued on a process‑wide `TiebreakQueue` and drained by a daemon thread, which appends `AI_TIEBREAK_SUGGESTED` events (additive signal only, never an auto‑close).

---

## Guardrails (non‑negotiable)

- The hidden `answer_key.json` must **never** reach matcher scope.
- Exceptions are **event‑sourced**: never `UPDATE` status in place; append to `exception_events`.
- **LLM = last resort** (Stage 5, async, never sole authority; capped at 84, never closes).
- **Maker proposes, Checker closes.**
- Synthetic data only — INR/paise integers, no real financial data.

Domain decisions, constraints, glossary and reason codes are locked in `docs/` (`decisions.md`, `constraints.md`, `glossary.md`, `taxonomy.md`).

---

## Development

- Always use the `.venv` (never system Python).
- Run tests: `python -m pytest backend/tests/` (expect 62 passing).
- Follow `AGENTS.md` for workflow, doc‑update rules and commit discipline (conventional commits per milestone).
