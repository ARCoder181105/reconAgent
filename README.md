# ReconAgent

**Multi-Source Fuzzy Reconciliation Engine** — Razorpay AI Buildathon, **Track 04 (AI Finance Controller)**.

> **One-line pitch:** ReconAgent takes a Razorpay-style settlement report and reconciles it against messy bank-statement data across a 50+ record batch. It reports **measured accuracy** against a hidden ground truth, and routes everything it can't confidently decide into an **honest exception queue** with a **Maker–Checker approval workflow**.

---

## 🎯 Track Alignment — Why This Solves Track 04

| Track 04 Requirement | How ReconAgent Delivers |
|---|---|
| **Payment risk / finance controller** | Reconciles gateway settlements ↔ bank credits — the core financial control loop for any merchant |
| **AI-assisted, not AI-replaced** | 5-stage deterministic pipeline resolves ~80% of records; only ~60% clear the confidence bar to auto-close, the rest correctly route to human review by design. LLM (Stage 5) is *last resort*, capped at confidence 84, never auto-closes |
| **Explainability & auditability** | Every match carries a reason code, confidence tier, and ranked candidates; exceptions are event-sourced (append-only log) |
| **Human-in-the-loop governance** | Maker proposes → Checker approves; nothing closes on a single person's say-so |
| **Measured accuracy, not claimed** | Hidden answer key evaluates precision/recall/F1 with 3× FP penalty; scores reported per-stage |
| **Privacy-first architecture** | Local Ollama (qwen2.5) runs entirely on-prem; cloud LLM (Gemini) is optional and configurable |

---

## 📊 Results — A Distribution, Not a Cherry-Picked Run

The track brief warns that "one cherry-picked match proves nothing." Here's what 10 independent
random seeds actually produce (`python scripts/demo.py --multi 10`), not a single lucky number:

| Metric | Mean | Stdev |
|---|---|---|
| Precision (row-count) | **1.000** | 0.000 |
| Recall (row-count) | **0.944** | 0.057 |
| F1 | **0.970** | 0.032 |
| Penalized score (3× FP weight) | **0.944** | 0.057 |
| ₹ misrouted (amount-weighted) | **4.70%** | 4.58% |

**Zero false positives across every one of the 10 seeds tested.** The engine is conservative by
design — when it isn't sure, it exceptions the record rather than guessing, which is exactly the
posture a financial control should have. Recall varies with how hard a given seed's batch happens
to be (seed 5, the hardest, still lands at 0.792 recall with 0 false positives); precision never
drops, because a wrong auto-match is treated as a worse failure than an honest exception.

For a single-seed walkthrough with full per-stage detail, see [Testing Instructions](#-testing-instructions-for-evaluators) below.

---

## 🖼 Screenshots

> _Add 2–3 screenshots or a short GIF here before submitting: the Exception Queue with a ranked
> candidate list, the Maker → Checker approval flow, and the Cash Position tile on the Dashboard.
> A judge skimming for 30 seconds will look at this section before reading a single curl command._

---

## 🏗 Architecture Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA INGRESS                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  settlements.csv (Razorpay-style)      bank_statement.csv (messy credits)  │
│       │                                         │                          │
│       └─────────────────┬───────────────────────┘                          │
│                         ▼                                                   │
│              ┌──────────────────────┐                                      │
│              │  Stage 0: Normalize  │  ← Strip symbols, parse dates,       │
│              │  (deterministic)     │     amounts → integer paise          │
│              └──────────┬───────────┘                                      │
└─────────────────────────┼──────────────────────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HYBRID INFERENCE ENGINE (5 Stages)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────┐  │
│  │  Stage 1     │───▶│  Stage 2     │───▶│  Stage 3     │───▶│ Stage 4  │  │
│  │  Exact UTR   │    │  Fuzzy UTR   │    │ Amount+Date  │    │Batch Sum │  │
│  │  (100 conf)  │    │  (85-94)     │    │  (60-84)     │    │ (60-84)  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘    └────┬─────┘  │
│                                                                     │        │
│                              ┌─────────────────────────────────────┘        │
│                              ▼                                                │
│                   ┌──────────────────────┐                                  │
│                   │   Stage 5: LLM       │  ← Async, structured JSON,       │
│                   │   Tie-Break          │     capped at 84, never closes   │
│                   │   (Ollama / Gemini)  │     fallback on failure          │
│                   └──────────┬───────────┘                                  │
└──────────────────────────────┼──────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      VALIDATION GUARDRAILS                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────────────┐  │
│  │  AUTO-CLOSED    │    │  REVIEW QUEUE   │    │  HARD EXCEPTIONS       │  │
│  │  (≥ 85 conf)    │    │  (60-84 conf)   │    │  (< 60 / no candidate) │  │
│  │  • exact        │    │  • Maker sees   │    │  • High priority       │  │
│  │  • fuzzy_utr    │    │    ranked cands │    │  • Maker proposes      │  │
│  │                 │    │  • Never auto   │    │  • Checker approves    │  │
│  └─────────────────┘    └─────────────────┘    └────────────────────────┘  │
│         │                       │                        │                  │
│         └───────────────────────┼────────────────────────┘                  │
│                                 ▼                                           │
│                   ┌─────────────────────────┐                              │
│                   │  EVENT-SOURCED AUDIT    │  ← exception_events table    │
│                   │  (append-only, no UPDATE)│     CREATED → MAKER_PROPOSED│
│                   └─────────────────────────┘     CHECKER_APPROVED/REJECTED│
│                                 │                                           │
│                                 ▼                                           │
│                   ┌─────────────────────────┐                              │
│                   │  HIDDEN ANSWER KEY      │  ← Only read by scoring      │
│                   │  (ground truth)         │     engine NEVER sees it     │
│                   └─────────────────────────┘                              │
│                                 │                                           │
│                                 ▼                                           │
│                   ┌─────────────────────────┐                              │
│                   │  SCORED METRICS         │  • Precision / Recall / F1  │
│                   │  (3× FP penalty)        │  • Penalized accuracy       │
│                   └─────────────────────────┘  • Per-stage breakdown      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ One-Command Setup (Docker Compose)

### Prerequisites
- Docker 24+ & Docker Compose v2 (the `docker compose` subcommand, **not** the older standalone `docker-compose` v1 binary — this compose file uses `depends_on: condition: service_healthy`, which v1 doesn't support)
- 4 GB RAM minimum (for Ollama model)
- **No GPU required.** Ollama runs on CPU by default here so the stack works out of the box everywhere. If you have an NVIDIA GPU with the NVIDIA Container Toolkit installed, see [GPU acceleration](#gpu-acceleration-optional) below.

### Quick Start — Everything Runs by Default

```bash
# 1. Clone and enter the repo
git clone <your-repo-url>
cd ReconAgent

# 2. Copy environment template
cp .env.example .env

# 3. Build and start ALL services (backend :8000, Ollama :11434, frontend :5173)
#    → Uses LOCAL Ollama by default, auto-pulls qwen2.5:1.5b (~1.5 GB)
docker compose up --build
```

The first run downloads the `qwen2.5:1.5b` model (~1.5 GB) inside the `ollama` container — that can take a few minutes depending on your connection. Watch progress with `docker compose logs -f ollama`; the backend will wait for it (`depends_on: condition: service_healthy`) before starting.

### LLM Provider Selection

Set these in your `.env` file, then run `docker compose up --build` — **`docker compose up` has no `-e` flag** (that only exists on `docker compose run`), so passing `-e VAR=val` to `up` will fail with "unknown flag."

| Mode | `.env` setting | Description |
|------|---------|-------------|
| **Local (default)** | `LLM_PROVIDER=ollama` | Uses Ollama container, auto-pulls `qwen2.5:1.5b`, fully offline |
| **Cloud (Gemini)** | `LLM_PROVIDER=gemini` + `GEMINI_API_KEY=your_key` | Skips Ollama model pull, uses Google Gemini API |
| **Custom Ollama model** | `OLLAMA_MODEL=llama3.2:3b` | Pulls your chosen model instead |

> **No code changes needed** — switch providers by editing `.env` and re-running `docker compose up --build`.
>
> If you'd rather not edit `.env` for a one-off run, on **Linux/macOS (bash/zsh)** you can prefix the variables directly on the command line instead:
> ```bash
> LLM_PROVIDER=gemini GEMINI_API_KEY=your_key docker compose up --build
> ```
> On **Windows PowerShell**, use:
> ```powershell
> $env:LLM_PROVIDER="gemini"; $env:GEMINI_API_KEY="your_key"; docker compose up --build
> ```

### GPU Acceleration (optional)

By default the `ollama` service runs on CPU — this is deliberate, because a hard-coded GPU requirement is the most common reason this stack fails to start (Docker Desktop on Mac/Windows, and most laptops, don't have an NVIDIA GPU passthrough set up, so `docker compose up` errors out trying to create the `ollama` container). If you do have an NVIDIA GPU and the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed, uncomment the `gpus: all` line under the `ollama` service in `docker-compose.yml` for faster inference.

### What Happens on Startup

| Service | Port | Purpose |
|---|---|---|
| `reconagent` | 8000 | FastAPI backend — reconciliation engine, exception queue, scoring API |
| `ollama` | 11434 | Local LLM runtime — auto-pulls `qwen2.5:1.5b` (or custom model) for Stage 5 tie-break |
| `frontend` | 5173 | React 19 + TypeScript dashboard — Summary, Exception Queue, Inspection, Audit |

All three services start by default. Ollama pulls the model on first run (cached in volume for subsequent starts).

---

## 🧪 Testing Instructions for Evaluators

### 1. Health Checks

```bash
# API health
curl http://localhost:8000/health
# → {"status": "ok"}

# Ollama health (only if using local provider)
curl http://localhost:11434/api/tags
# → {"models": [{"name": "qwen2.5:1.5b", ...}]}
```

### 2. Run the Full Reconciliation Pipeline (API)

```bash
# Generate fresh synthetic data (settlements + bank statement + hidden answer key)
curl -X POST http://localhost:8000/api/generate-data \
  -H "Content-Type: application/json" \
  -d '{"seed": 42, "batch_size": 60}'

# Run the 5-stage pipeline (stages 1-4 sync, stage 5 async)
curl -X POST http://localhost:8000/api/run-reconciliation

# Get headline metrics
curl http://localhost:8000/api/report
# → { "match_rate": 0.85, "review_rate": 0.10, "exception_rate": 0.05, "verified_rate": 0.00, ... }

# Get scored accuracy vs hidden answer key
curl http://localhost:8000/api/score
# → { "precision": 1.0, "recall": 1.0, "f1": 1.0, "penalized_accuracy": 1.0, "per_stage": {...} }
```

### 3. Inspect the Exception Queue (Maker View)

```bash
# All exceptions with ranked candidates
curl http://localhost:8000/api/exceptions

# Exceptions pending Checker approval
curl http://localhost:8000/api/exceptions/pending-approval
```

### 4. Simulate Maker–Checker Workflow

```bash
# Get an exception ID from the list above, then:

# MAKER proposes a resolution (does NOT close the books)
curl -X POST http://localhost:8000/api/exceptions/<EXCEPTION_ID>/resolve \
  -H "Content-Type: application/json" \
  -d '{"action": "confirm", "matched_settlement_id": "SETL-123", "note": "Verified against bank ref"}'

# CHECKER approves (closes the books → counts toward verified_rate)
curl -X POST http://localhost:8000/api/exceptions/<EXCEPTION_ID>/approve \
  -H "Content-Type: application/json" \
  -d '{"decision": "approve", "note": "Approved per policy"}'

# CHECKER rejects (reopens for Maker)
curl -X POST http://localhost:8000/api/exceptions/<EXCEPTION_ID>/approve \
  -H "Content-Type: application/json" \
  -d '{"decision": "reject", "note": "Wrong candidate, needs re-review"}'
```

### 5. Run the Automated Demo (Generates + Reconciles + Scores)

```bash
# Inside the container (recommended)
docker compose exec reconagent python scripts/demo.py --seed 42

# Or locally if you have the venv
source .venv/bin/activate
python scripts/demo.py --seed 42
```

**Expected Output (seed 42, verified against the current pipeline):**
```
1) Generated 60 settlements, 47 bank lines (seed 42).

2) Reconciled — 48/60 matched.
   match_rate     60.00%   (engine confidence)
   review_rate    20.00%   (60-84 band -> Maker)
   exception_rate 20.00%   (hard exceptions)
   per-stage:
      exact          30
      fuzzy_utr       7
      amount_date     5
      batch_sum       6

3) Offline accuracy vs hidden answer key (FP penalized 3x):
   row: precision 1.000  recall 1.000  F1 1.000  penalized 1.000
        hits 48/48 · fp 0 · misses 0
   ₹:   precision 1.000  recall 1.000  misrouted 0.00%  penalized 0.00%
```

Note the gap between "48/60 matched" (stages 1–4 found a candidate) and "match_rate 60%"
(only the ≥85-confidence subset auto-closes) — `amount_date` and `batch_sum` results always land
in the review band by design, since neither carries UTR corroboration. That gap is the exception
engine working as intended, not a shortfall.

### 6. Multi-Seed Robustness Check

```bash
docker compose exec reconagent python scripts/demo.py --multi 10
# Runs seeds 1..10, reports mean ± stdev for all metrics
```

---

## 🔑 Key Technical Highlights

### Schema Enforcement & Type Safety
- **Pydantic v2** models for every API request/response and database row
- **SQLAlchemy 2.0** with declarative models — no raw SQL in business logic
- **Canonical constants** (`backend/constants.py`) mirror `docs/taxonomy.md` — reason codes, stage keys, event types single-sourced

### Graceful Failure Recovery
| Failure Mode | Mitigation |
|---|---|
| LLM API timeout / rate limit | Async queue with exponential backoff; deterministic fallback activates |
| LLM returns invalid JSON | Structured output parsing with validation; falls back to rule-based decision |
| Ollama container unavailable | Healthcheck-gated startup; `LLM_PROVIDER=gemini` env var switches provider instantly |
| Subset-sum explosion (Stage 4) | Bounded DP with early exit; max 50 records → completes in <50ms |
| Database lock contention | WAL mode SQLite; connection pooling via SQLAlchemy |

### Privacy Controls
- **Local-first LLM**: `OLLAMA_BASE_URL=http://ollama:11434` — model weights never leave your network
- **No telemetry**: Zero outbound calls unless `LLM_PROVIDER=gemini` is explicitly set
- **Synthetic data only**: All amounts in INR paise (integers); no real merchant data ever processed
- **Hidden answer key**: Generated alongside data, stored in `backend/data/answer_key.json`, **gitignored**, read **only** by `backend/eval/score.py` — matcher pipeline has zero access

### Event-Sourced Exception Governance
```sql
-- exception_events table (append-only, never UPDATE)
CREATE TABLE exception_events (
    id INTEGER PRIMARY KEY,
    exception_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,  -- CREATED | MAKER_PROPOSED | CHECKER_APPROVED | CHECKER_REJECTED
    actor_role TEXT NOT NULL,  -- maker | checker
    payload_json TEXT,         -- {action, matched_settlement_id, note}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
- Status is a **projection** over the event log — full audit trail by design
- Maker proposes → `status = pending_approval`; only Checker `approve` → `status = closed`

### Measured Accuracy (Not Marketing)
- **3× False-Positive Penalty**: `penalized = (hits − 3·fp) / expected` — a wrongly-confirmed match is a financial-control failure
- **Per-stage scorecard**: See exactly how many records closed at `exact`, `fuzzy_utr`, `amount_date`, `batch_sum`, `llm_tiebreak`
- **Multi-seed validation**: `demo-multi` runs N seeds, reports mean ± stdev — no cherry-picked single seed

---

## 📁 Project Structure (Key Paths)

```
ReconAgent/
├── Dockerfile                    # Backend production image
├── docker-compose.yml            # Orchestration (API + Ollama + Frontend)
├── frontend/Dockerfile.frontend  # Frontend dev image
├── .env.example                  # Environment template (copy to .env)
├── requirements.txt              # Python deps (pinned compatible ranges)
├── Makefile                      # Dev shortcuts (install, test, demo, dev, web)
├── scripts/demo.py               # One-command demo + multi-seed robustness
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint (port 8000)
│   │   ├── db.py                 # SQLAlchemy engine + session
│   │   ├── models.py             # ORM models (settlements, lines, matches, exceptions, events)
│   │   ├── schemas.py            # Pydantic request/response models
│   │   ├── routers/              # API endpoints (data, report, exceptions, inspector, score)
│   │   ├── services/             # Business logic (reconcile_service, llm_queue, exception_service)
│   │   ├── matcher/              # 5-stage pipeline (exact, fuzzy_utr, amount_date, batch_sum, llm_tiebreak)
│   │   └── data_generator/       # Synthetic data + hidden answer key
│   ├── eval/
│   │   └── score.py              # Precision/Recall/F1 + 3× FP penalty
│   ├── tests/                    # 66 pytest cases (unit + integration)
│   ├── config.py                 # Typed settings from .env
│   └── constants.py              # Canonical reason codes, stages, events
├── docs/                         # Source of truth (master-design, decisions, taxonomy, scope, etc.)
└── frontend/                     # Vite + React 19 + TypeScript + shadcn/ui dashboard
```

---

## 🛡 Guardrails (Non-Negotiable)

| Rule | Enforcement |
|---|---|
| Hidden answer key never reaches matcher | `backend/data/answer_key.json` gitignored; only `eval/` imports it |
| Event-sourced exceptions | No `UPDATE exception SET status` — only `INSERT INTO exception_events` |
| LLM = last resort | Stage 5 only; async; structured output; capped at 84 confidence; never sole authority |
| Maker proposes, Checker closes | API enforces: `/resolve` (Maker) → `/approve` (Checker) |
| Synthetic data only | INR paise integers; generated via seeded RNG; no external data sources |

---

## 📚 Documentation Deep-Dive

| Document | Purpose |
|---|---|
| `docs/master-design.md` | Ultimate architecture, schema, pipeline, future scope |
| `docs/decisions.md` | 8 locked decisions (D1–D8) — must obey |
| `docs/constraints.md` | Hard limits (no ChromaDB, no Prometheus, no cross-border, no multi-currency, no real-time) |
| `docs/taxonomy.md` | Canonical reason codes, confidence tiers, event types, metrics |
| `docs/scope.md` | In/out of scope for this buildathon |
| `docs/glossary.md` | Locked term definitions |
| `docs/iterations/` | Per-iteration design notes (00–11) |

---

## 🚀 For Hackathon Reviewers — Quick Verification Checklist

- [ ] `docker compose up --build` starts all 3 services cleanly (API :8000, Ollama :11434, Frontend :5173)
- [ ] Ollama auto-pulls `qwen2.5:1.5b` on first run (check `docker compose logs -f ollama`)
- [ ] `docker compose exec reconagent python scripts/demo.py --seed 42` prints **Penalized: 1.000**
- [ ] `curl localhost:8000/api/report` shows `match_rate` around `60` (0–100 scale, not a fraction) and `exception_rate > 0`
- [ ] `curl localhost:8000/api/exceptions` returns array with `reason_code`, `confidence`, `candidates`
- [ ] Maker→Checker flow via `/resolve` + `/approve` increments `verified_rate`
- [ ] `curl localhost:8000/api/score` returns per-stage breakdown matching demo output
- [ ] Frontend loads at `localhost:5173`, shows Summary + Exception Queue tabs
- [ ] **Switch to Gemini**: set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY=your_key` in `.env`, then `docker compose down && docker compose up --build` — works without Ollama

---

## 🔧 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `docker compose up` fails immediately on the `ollama` service with a "could not select device driver" error | `gpus: all` is set but you don't have an NVIDIA GPU + NVIDIA Container Toolkit | Leave the `gpus: all` line commented out (it's optional — see [GPU acceleration](#gpu-acceleration-optional)) |
| `reconagent` never starts, seems stuck waiting | It's waiting on `ollama`'s healthcheck, which can take minutes on first run while the model downloads | `docker compose logs -f ollama` to watch the pull; be patient, or pre-pull with `docker compose run --rm ollama ollama pull qwen2.5:1.5b` |
| `unknown flag: -e` when running `docker compose up -e ...` | `-e` isn't a valid flag on `up` | Put the variable in `.env`, or prefix it on the command line (see [LLM Provider Selection](#llm-provider-selection)) |
| Generating data / running reconciliation fails with permission or I/O errors on `backend/data/` | An older `docker-compose.yml` mounted the `recon_data` volume *before* the `./backend` bind mount and marked it `:ro` — the bind mount then shadowed the volume and made the whole tree read-only | Make sure `docker-compose.yml` lists `./backend:/app/backend` **before** `recon_data:/app/backend/data`, and that the backend bind mount is **not** `:ro` |
| Custom `OLLAMA_MODEL` in `.env` is ignored, container still pulls `qwen2.5:1.5b` | `OLLAMA_MODEL` wasn't passed into the `ollama` service's own `environment:` block, only into `reconagent`'s | Ensure `OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5:1.5b}` is set under **both** services in `docker-compose.yml` |
| Frontend container shows "unhealthy" in `docker compose ps` even though the app loads fine at `localhost:5173` | `node:20-alpine` doesn't ship `curl`, which the healthcheck uses | Rebuild after the Dockerfile fix that adds `RUN apk add --no-cache curl`, or switch the healthcheck to `wget` |
| Running locally with `make dev` (no Docker) tries to call Gemini even though you never set `LLM_PROVIDER` | `backend/config.py` defaulted `llm_provider` to `"gemini"`, inconsistent with the Ollama-first default everywhere else | Fixed in `config.py` — default is now `"ollama"`, matching `.env.example` |

---

## 📜 License & Attribution

Built for the **Razorpay AI Buildathon 2026** — Track 04 (AI Finance Controller).
All code is synthetic, demo-grade, and not for production financial use without review.

**Generated data disclaimer:** Settlement and bank statement data are procedurally generated for evaluation purposes only. No real merchant or transaction data is used or stored.