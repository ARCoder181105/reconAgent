# ReconAgent

**Multi-Source Fuzzy Reconciliation Engine** — Razorpay Buildathon, Track 04 (AI Finance Controller).

ReconAgent takes a Razorpay-style **settlement report** and reconciles it against **messy bank-statement data** across a 50+ record batch. It doesn't just "match things up" — it reports **measured accuracy** against a hidden ground truth, and routes everything it can't confidently decide into an **honest exception queue** with a **Maker–Checker approval workflow**. The whole loop — *generate → run → review → resolve → approve → measure* — lives in a React dashboard.

> **Pitch: verification capacity, not generation speed, is the bottleneck.** ReconAgent is built to make the *remaining unknowns* visible and resolvable, and to report its own accuracy honestly — never to imply it "matched everything."

The authoritative design, locked decisions, constraints, and taxonomy live in [`docs/`](docs/) — see [`docs/sources-of-truth.md`](docs/sources-of-truth.md) for precedence.

---

## Why this exists

Every merchant that sells online gets paid by the gateway in **settlement batches**, but the bank statement shows **individual credits** — and the two never line up cleanly. Fees and GST are netted, payments are batched, refunds are deducted, references get truncated, amounts drift by a few rupees. Reconciling a 50+ record month by hand is slow and error-prone.

ReconAgent automates the *definable* 90% and hands a human only the genuinely ambiguous 10% — with ranked candidates and a clear reason code — then closes the loop through a two-person approval flow so nothing is ever booked on a single person's say-so.

---

## Status

- **Iterations 0–11 complete & committed** — full stack: data generator, 5-stage matcher, exception engine, offline scoring, FastAPI backend, async LLM tie-break, React dashboard, and a one-command demo pack.
- **Accuracy**: seed‑42 eval **48/48, precision 1.0, recall 1.0, F1 1.0, penalized 1.0**, **0 false positives** (recall +6.25 to +8.33pp across seeds 42/43/44/45/7/123).
- **Tests**: 66 backend tests passing; `npm run build` clean.

---

## Quickstart (demo)

```bash
# 1. Create the virtualenv and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. One-command demo: generate → reconcile → score → headline numbers
make demo                # or: python scripts/demo.py

# 3. Run the dashboard (needs two terminals)

# terminal A — backend API on :8000
make dev

# terminal B — frontend dev server on :5173
make web-install         # first time only
make web
```

Open `http://localhost:5173`. Click **Run reconciliation** to generate fresh data and reconcile, review exceptions as the **Maker**, approve them as the **Checker** in the Pending Approval tab, and watch **verified rate** rise on the Summary.

---

## What "reconciliation" means here

Reconciliation is **confirming that each gateway settlement actually arrived at the bank, as the correct credit, for the correct amount and reason** ([`glossary.md`](docs/glossary.md)). Every number on the board is honest and measured — in particular:

| Metric | Formula | What it tells you |
|---|---|---|
| **Match rate** | `auto_matched / total` | Engine *confidence* — which records the pipeline closed on its own. |
| **Review rate** | `review_queue / total` | Records that landed in the 60–84 band and *need a human* (Maker). |
| **Exception rate** | `hard_exceptions / total` | High-priority records the engine couldn't decide. |
| **Verified rate** | `records_closed / total` | Books *actually closed* after a Checker signed off. |

> `match_rate` ≠ `verified_rate` on purpose (locked decision **D6**). The first is what the machine *thinks*; the second is what a human *confirmed*. Reporting them separately is a core guarantee of the product.

---

## How the pipeline works

The engine is a **staged, explainable pipeline**, not a single fuzzy blob (locked decision **D1**). A record only advances to a less-certain stage if all earlier ones fail to close it. Each stage has a narrow, explainable rule, so a reviewer can always see *why* a record was matched or escalated.

```
settlements.csv  ─┐
                  ├→  Stage 0  Normalize
bank_statement.csv─┘        │
                            ▼
                  Stage 1  Exact UTR (confidence 100)
                         │  Stage 2  Fuzzy UTR (85–94)
                         ▼  Stage 3  Amount + date (60–84)
                            │  Stage 4  Batch-sum (many-to-one)
                            ▼  Stage 5  LLM tie-break (last resort, ≤ 84)
                                      │
                                      ▼
                          auto-closed  ·  review queue  ·  hard exceptions
```

### Stage 0 — Normalize
Clean every field before any comparison: strip currency symbols and thousands separators, parse every date format into ISO 8601, uppercase text, and convert **all amounts to integer paise**. Downstream never compares raw, unnormalized strings.

### Stage 1 — `exact`
**Exact UTR substring + amount.** The full UTR string (e.g. `1568176960vxp0rj`) is found verbatim inside the bank line's description/ref number **and** `net_amount` matches the credit within ±₹1. Confidence **100** — this is the unambiguous, auto-closable case.

### Stage 2 — `fuzzy_utr`
**Fuzzy UTR via edit-distance.** The UTR in the bank description is often *garbled or truncated* (banks keep only the first or last N characters). The stage extracts a UTR-like token (a 12–18 character alphanumeric run) and scores it with **rapidfuzz** edit-distance, plus truncation-aware prefix/suffix checks. A candidate is accepted only if the amount is also within tolerance. Confidence scales with edit distance: **85–94** → auto-closed; lower → review.

> **Why "fuzzy"?** Because the reference isn't an identical copy-and-paste match — it's *close but not exact*: a truncated UTR, an OCR smudge, a dropped character. "Fuzzy" = matched by similarity, not equality.

### Stage 3 — `amount_date`
**Amount + date window, no UTR.** When the description is empty or unparseable, search for settlements whose `net_amount` matches the credit within a **±2 business-day window**. If exactly **one** candidate exists → accept at medium confidence (**60–84**, goes to review). If *more than one* settlement shares the amount in that window, the stage **refuses to guess** and flags the record as ambiguous rather than risk a wrong booking.

### Stage 4 — `batch_sum`
**Batch-sum: many settlements → one bank credit.** A single bank credit often aggregates *multiple* settlement records (T+2 batching). The stage searches subsets of the remaining unmatched pool whose `net_amount` values **sum to the credit** (±₹1) within a wider date window, via a **bounded subset-sum dynamic program** (plenty at 50+ records). Exactly one valid partition → accept (review band). Multiple valid partitions → flag `BATCH_PARTITION_AMBIGUOUS`.

### Stage 5 — `llm_tiebreak`
**LLM as a last resort (Gemini, async).** Records still unresolved advance to an asynchronous background queue. Gemini is used **only** with structured (fixed-JSON) output, and its suggestion can lift confidence to at most **84** — it can **never auto-close** an exception (decisions **D5**, guardrail). On any failure it degrades to a deterministic fallback. It appends an *additive* `AI_TIEBREAK_SUGGESTED` event for a human to weigh — never a self-approval.

### The two outputs
- **Auto-closed (≥ 85):** the engine is confident; logged for the audit trail.
- **Exceptions (< 85 or ambiguous):** routed to the queue with a **reason code**, a **confidence**, and **ranked candidates** for a human.

---

## Exceptions, reason codes & confidence tiers

A **score alone isn't decision-ready** — so every exception carries a reason *and* a confidence band.

| Confidence | Tier | Action |
|---|---|---|
| ≥ 95 | Auto-match | Close automatically |
| 85–94 | Auto-match | Close automatically, log basis |
| 60–84 | Review queue | **Human review required (Maker)** |
| < 60 / no candidate | Hard exception | Review required, high priority |

**Reason codes** explain *why* it couldn't decide ([`taxonomy.md`](docs/taxonomy.md) — canonical, don't invent new ones):

| Code | Meaning |
|---|---|
| `NO_CANDIDATE` | No settlement candidate found at all |
| `MULTIPLE_CANDIDATES` | More than one plausible candidate — can't decide (e.g. duplicate-amount trap) |
| `AMOUNT_MISMATCH` | Candidate found but amount outside tolerance |
| `UTR_UNRESOLVED` | UTR too garbled/truncated to resolve |
| `DATE_OUT_OF_WINDOW` | No candidate within the acceptable date window |
| `BATCH_PARTITION_AMBIGUOUS` | Multiple valid subset-sum partitions for one batch credit |

Each exception keeps its **ranked top candidates** (settlement ↔ line, with scores) so a reviewer sees not just "failed" but *what it almost matched against*.

---

## Maker–Checker governance

A financial exception is rarely resolved by one person, so closing the books is a **two-role** flow (decision **D6**, event-sourced):

```
Engine flags exception
        │  (append CREATED)
        ▼
MAKER  proposes a resolution   confirm / reject / override
        │  (append MAKER_PROPOSED → status = pending_approval)
        ▼
CHECKER  signs off             approve (closes)  ·  reject with reason (reopens)
        │  (append CHECKER_APPROVED / CHECKER_REJECTED)
        ▼
book closed  →  counted in verified_rate
```

- **Maker** — proposes. A proposal **never** closes the books.
- **Checker** — signs off. Only this closes the books.
- **Event sourcing (D2)** — status is a **projection** over an **append-only `exception_events` log**; nothing is ever `UPDATE`d in place. A WYSIWYG audit trail is the system of record.
- The dashboard splits per-stage counts into **auto vs review**, so it's obvious which stages close themselves and which always reach the human.

---

## The hidden answer key (what it's for)

The matcher works from **only the two CSVs** — it never sees the answer key ([`glossary.md`](docs/glossary.md), guardrail). The key is generated *with* the data (because the project synthesizes its own ground truth, decision **D3**) and is read **only by the scoring path** to grade the engine afterward:

1. **Generate** → writes `settlements.csv`, `bank_statement.csv`, **and** the hidden `answer_key.json` (the known-correct settlement↔line mapping).
2. **Match** → the 5-stage pipeline consumes only the two CSVs. It has no idea what the "right" answer is.
3. **Score** → the eval compares the engine's matches to the answer key and computes precision / recall / F1 / weighted accuracy.

> **Why hidden?** If the matcher ever read it, it would be *cheating* — "knowing the answers" instead of genuinely reconciling. It's like a student answering from the question paper; the answer key is the teacher's grading sheet.

---

## Scoring & the 3× false-positive penalty

Accuracy is **measured**, not assumed ([`backend/eval/score.py`](backend/eval/score.py)):

- **Precision** = TP / (TP + FP), **Recall** = TP / (TP + FN), **F1** = harmonic mean.
- **False positives are penalized 3×** (decision **D7**): `penalized = (hits − 3·fp) / expected`. A wrongly-confirmed match is a *financial-control failure*; an over-cautious exception is a minor inconvenience. This deliberately stops the engine from chasing recall by guessing.
- The scorecard also reports **per-stage counts** (decision **D8**), so you can see exactly how many records closed at each stage.

---

## Architecture

```
backend/
  app/
    data_generator/     # synthetic data + hidden answer key
    matcher/            # normalizer + exact, fuzzy_utr, amount_date, batch_sum,
                        #   reconcile (orchestration), llm_tiebreak (stage 5)
    services/           # reconcile_service + llm_queue (async background)
    routers/            # data, report, exceptions, inspector, score
    db.py  models.py  schemas.py
  eval/                 # offline scoring vs answer key
  tests/                # pytest suite
  config.py  constants.py
docs/                   # design + domain source of truth
frontend/               # Vite + React 19 + TypeScript + shadcn/ui dashboard
scripts/demo.py         # one-command demo
```

- **Data flow:** `run-reconciliation` runs stages 1–4 synchronously and returns the deterministic report immediately. Eligible unresolved lines are enqueued on a process-wide `TiebreakQueue`, drained by a background thread, and appended as `AI_TIEBREAK_SUGGESTED` events — additive signal only, never an auto-close.
- **Frontend:** fully client-side against the API. Pages stay presentational; every state transition happens through the underlying contract, so the dashboard can land on top of a clean backend with zero business logic duplicated. See `docs/iterations/` for per-iteration design.

### Terms you'll see in the code & docs

| Term | Meaning |
|---|---|
| **settlement** | A group of captured payments, netted (minus fees, tax, refunds, adjustments), transferred to the merchant. |
| **UTC / statement line** | An individual credit (or debit) on the bank statement. |
| **UTR** | Unique Transaction Reference — the bank's identifier for a single transfer. |
| **fuzzy_utr** | A UTR matched by similarity (edit distance) rather than exact equality. |
| **batch_sum** | One bank credit that equals the *sum* of several settlement records (many-to-one). |
| **llm_tiebreak** | Stage 5 — an LLM plausibility judgment on unresolved records (last resort). |
| **reason code** | The canonical classifier of why a record is an exception. |
| **candidates** | Top 1–3 closest proposed matches (with scores) shown to a reviewer. |
| **exact / fuzzy_utr / amount_date / batch_sum / llm_tiebreak** | The five `matches.stage` identifiers in the database. |

---

## Getting started (full)

Requires **Python 3.12.3** (pinned in `.python-version`) and Node 18+ for the frontend.

```bash
# Install backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment (LLM key optional; only needed for Stage 5)
cp .env.example .env        # fill in GEMINI_API_KEY if you want the LLM tie-break

# Install + run frontend
make web-install
make dev                     # backend  :8000
make web                     # frontend :5173  (separate terminal)
```

### CLI / Makefile targets

```bash
make install      # install requirements into .venv
make test         # run backend/tests (66)
make gen          # generate synthetic data (settlements.csv, bank_statement.csv, answer_key.json)
make score        # offline scoring vs hidden answer key (3x fp penalty), seed 42
make demo         # one-command: generate + reconcile + score + headline numbers
make demo-multi   # multi-seed robustness (mean/stdev), default N=10
make dev          # uvicorn backend.app.main:app --reload
make web          # Vite dev server
make web-build    # type-check + build frontend
make clean        # remove venv + generated data + caches
make help         # list all targets
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

Interactive docs auto-generate at `/docs` once the server is running.

---

## Guardrails (non-negotiable)

- The hidden `answer_key.json` must **never** reach matcher scope; it is only read by `backend/eval/` and `scripts/demo.py`.
- Exceptions are **event-sourced**: never `UPDATE` status in place; append to `exception_events`.
- **LLM = last resort** (Stage 5, async, never sole authority; capped at 84, never closes).
- **Maker proposes, Checker closes.**
- **Synthetic data only** — modeled INR/paise integers, no real financial data. Do not treat it as real merchant data.

Domain decisions, constraints, glossary, and reason codes are locked in `docs/` (`decisions.md`, `constraints.md`, `glossary.md`, `taxonomy.md`).

---

## Development

- Always use the `.venv` (never system Python).
- Run tests: `python -m pytest backend/tests/` (66 passing).
- Follow `AGENTS.md` for workflow, doc-update rules, and commit discipline (conventional commits per milestone).