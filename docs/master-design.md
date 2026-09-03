# Multi-Source Fuzzy Reconciliation Engine
## Master Project Document — Razorpay Buildathon, Track 04: AI Finance Controller

**Project codename:** ReconAgent
**Track objective addressed:** Run the books and the cash position — close one finance-ops loop across a 50+ record batch, reporting measured match rate and an honest exception list.

---

## 1. Executive Summary

ReconAgent is an AI-assisted reconciliation engine that matches a Razorpay-style settlement report against a deliberately messy bank statement. It runs a staged pipeline — exact match, fuzzy UTR match, amount/date match, batch-sum (many-to-one) match, and an LLM tie-break of last resort — and produces two things every finance team actually needs: a **measured match rate** and an **honest, ranked exception queue** for whatever it could not confidently resolve on its own.

The project is built around three judging criteria stated in the track brief, and every design decision below is traceable to one of them:

| Judging criterion | How ReconAgent addresses it |
|---|---|
| Throughput | Processes the full batch (50+ records) in one run, no manual pre-filtering, no cherry-picked "demo" rows. |
| Measured accuracy | Synthetic ground truth with a hidden answer key enables real precision/recall scoring, not a vibes-based demo. |
| Honest exception list | Every unresolved record gets a reason code, a confidence score, and ranked candidate matches — never silently dropped. |

---

## 2. Domain Deep-Dive: How a Payment Becomes a Bank Credit

Understanding this lifecycle is the foundation for every schema and matching rule in this document.

### 2.1 The lifecycle, step by step

1. **Capture** — Customer pays via UPI, card, netbanking, or wallet. Razorpay (the payment gateway) captures the payment and holds it in a pooled account. The payment is now `captured`, not yet settled to the merchant.
2. **Batching** — Razorpay groups multiple captured payments, across customers and payment methods, into a settlement cycle. Default cycle is T+2 business days; some merchants have T+1 or same-day/instant settlement (at an extra fee).
3. **Deduction** — Before the batch is transferred, Razorpay deducts its fee (MDR — Merchant Discount Rate, commonly around 2% depending on payment method) plus 18% GST on that fee. Any refunds or chargebacks processed within the cycle are also netted into the same batch.
4. **Transfer** — The net amount is sent to the merchant's bank account via NEFT, RTGS, or IMPS. The receiving bank assigns a UTR (Unique Transaction Reference) — a reference number that, in principle, uniquely identifies that transfer across the Indian banking system.
5. **Statement entry** — The merchant's bank reflects this as a single credit line in the bank statement, ideally carrying the UTR. In practice, the UTR is often truncated, reformatted, or buried inside a longer freeform narration string alongside branch codes and batch identifiers.
6. **Reconciliation** — The finance team must confirm, for every settlement batch, that the corresponding bank credit arrived, in the right amount, for the right reason. This is the step ReconAgent automates.

### 2.2 Real settlement data shape (grounded in Razorpay's actual API)

Razorpay's settlement entity genuinely carries: a settlement id (`setl_...`), `amount`, `status`, `fees`, `tax`, a `utr` string (e.g. `1568176960vxp0rj`), and a creation timestamp. Individual transaction-level records inside a settlement additionally carry `debit`/`credit`, `settled_at`, `settlement_id`, `settlement_utr`, `order_id`, `payment_id`, and `method`/`card_network` detail. This project's synthetic settlement schema (Section 4) mirrors that real shape deliberately, so the prototype's data isn't a toy — it's structurally identical to what a real Razorpay merchant account produces.

### 2.3 Why manual reconciliation breaks down — the failure modes ReconAgent must handle

- **Many-to-one batching** — one bank credit line represents the sum of dozens of individual payments, minus fees, tax, and refunds. The bank statement never shows this breakup.
- **UTR mangling** — banks frequently truncate the UTR (showing only the first 10–16 characters), reformat it, or embed it mid-string inside branch/batch codes rather than as a clean token.
- **Fee/tax drift** — the net settled amount never equals the gross payment amount; someone has to recompute MDR + GST to confirm the deduction was correct.
- **Date mismatch** — Razorpay's settlement-created date, the bank's value date, and the bank's processing date can differ by weekends and holidays. Two different batches can land in the statement on the same day.
- **On-hold / partial settlement** — risk holds pull some payments out of a batch, so today's settlement composition doesn't match what was expected from yesterday's payment list.
- **Refund/chargeback timing** — sometimes netted into the batch, sometimes appear as a standalone debit line with no settlement counterpart at all.
- **Orphan bank lines** — bank charges, TDS deductions, escrow fees appear in the statement with no matching settlement record, ever.
- **Rounding** — paise-level differences between systems.
- **Zero audit trail** — the manual process is a VLOOKUP-on-UTR exercise in Excel with no confidence score and no record of *why* a match was accepted. Ambiguous cases get silently skipped and forgotten, which is exactly the gap this project closes.

---

## 3. Data Strategy: Synthetic Ground Truth + Real-World Texture

This is a deliberate two-layer approach, not a shortcut.

### 3.1 Why synthetic data is the backbone, not a compromise

No public dataset pairs a payment-gateway settlement report with a matching bank statement at merchant-record level with a known correct answer — that pairing is private financial data, and it is also the exact artifact this project produces. Public datasets that surface under search (e.g. RBI-published "Settlement Data of Payment Systems" on Kaggle) are aggregate, system-wide statistics — total NEFT/UPI/RTGS volume and value across the country — not row-level merchant records, and carry no ground-truth pairing at all.

The track's quality bar demands **measured accuracy**. Measuring accuracy requires already knowing the correct answer for each record, so the final report can state a real precision/recall number instead of an assertion. Only a synthetic dataset with a hidden answer key makes that possible.

### 3.2 Where real data adds value — texture, not ground truth

- **Narration realism**: harvest real narration string patterns (`NEFT-`, `IMPS-`, `UPI/`, `RTGS-` prefixes, real bank narration conventions) from publicly available Indian bank transaction datasets, and apply them as templates over the synthetic messy rows. Original labels/columns from these datasets are discarded entirely — only the string formatting patterns are reused.
- **Amount realism**: source a real e-commerce order-value distribution (several are available on Kaggle) to drive the underlying customer payment amounts, instead of uniform-random numbers. Real distributions cluster around price points (₹149, ₹899, ₹2,499, etc.) and make the demo data look authentic rather than generated.
- **Pitch narrative**: RBI's published system-wide settlement statistics can support one line in the pitch ("India processes crores of transactions daily, and reconciliation is still largely manual") — used as color for the presentation, not as row-level data.

### 3.3 The answer-key composition (hidden from the agent, used only for scoring)

The generator must produce both correct and incorrect cases, in a realistic mix — not a dataset of only hard cases, which would be unmeasurable, and not a dataset of only easy cases, which would prove nothing:

| Category | Share | Description |
|---|---|---|
| **True matches** | ~70% | Genuinely correct settlement-to-bank pairs, spread across difficulty: some exact-UTR (easy), some fuzzy/truncated-UTR (medium), some inside a batched credit line (hard). |
| **True exceptions** | ~20% | Deliberately unmatchable: orphan bank charges with no settlement behind them, settlements not yet credited, duplicate-amount traps where two unrelated settlements share an identical amount and no correct answer exists without more information. |
| **Ambiguous-but-resolvable** | ~10% | Matchable only with real work — a batch-sum split across 2–4 settlement records, or a fuzzy UTR match at a high edit distance. This is the band that actually tests the confidence tiering. |

The answer key (true settlement ↔ bank-line mapping, and the list of genuine orphans) is generated alongside the messy data but withheld from the matching pipeline. It is used only afterward, by a separate scoring script, to compute:

- **True positive**: agent auto-matched a pair that the answer key confirms is correct.
- **False positive**: agent auto-matched a pair that the answer key says is wrong — the most dangerous failure mode, since it means money was reconciled incorrectly with false confidence.
- **False negative**: agent sent a record to the exception queue that the answer key says had a confident correct match available.
- **True negative**: agent correctly flagged a genuine orphan as an exception.

**Scoring recommendation**: weight false positives more heavily than false negatives in the final accuracy score (e.g. a false positive costs 3x a false negative). A reconciliation agent that is occasionally too cautious is a minor inconvenience; one that is occasionally wrong with full confidence is a financial control failure. This weighting is configurable but should default to caution.

---

## 4. Data Schemas

### 4.1 `settlements.csv` — the structured, ground-truth side

| Column | Type | Notes |
|---|---|---|
| `settlement_id` | string | `setl_XXXXXXXXXXXX`, mirrors real Razorpay id format |
| `utr` | string | full UTR, e.g. `1597813219E1PQ6W` |
| `settlement_date` | date | `YYYY-MM-DD` |
| `no_of_transactions` | int | batch size — drives many-to-one cases |
| `gross_amount` | int (paise) | sum of captured payments in the batch |
| `fees` | int (paise) | MDR deducted |
| `tax_gst` | int (paise) | 18% GST on fees |
| `refunds_deducted` | int (paise) | can be 0 |
| `adjustments` | int (paise) | chargebacks etc., can be negative |
| `net_amount` | int (paise) | `gross − fees − tax − refunds + adjustments` |
| `status` | enum | `processed` / `on_hold` / `reversed` |
| `bank_account_last4` | string | for multi-account merchant scenarios |

### 4.2 `bank_statement.csv` — the messy, unstructured side

| Column | Type | Notes |
|---|---|---|
| `txn_date` | string | intentionally inconsistent formats: `05-09-2026`, `05/09/26`, `2026-09-05` |
| `value_date` | string | often blank |
| `description` | string (freetext) | messy — see examples below |
| `ref_no` | string | truncated/garbled UTR, sometimes blank |
| `debit` | float | blank if credit |
| `credit` | float | blank if debit |
| `balance` | float | running balance — noise, not used for matching |
| `bank_name` | string | e.g. HDFC, ICICI, Kotak |

### 4.3 Messy-data examples to seed deliberately

- **Truncated UTR**: `NEFT-1597813219E1P-RAZORPAY SOFTWARE PVT LTD` (last characters of the UTR dropped).
- **Bundled/batched credit**: one bank line, `credit = 487650.32`, that is actually the sum of 3 separate settlement records — nothing in the description indicates this.
- **Missing description**: `description = "BY TRANSFER-CLG"`, `ref_no = ""` — forces a pure amount+date match.
- **Mid-string UTR**: `CMS001/RZRPY/1597813219E1PQ6W/BATCH` — UTR sits at a variable offset, not a fixed position.
- **Off-by-fee amount**: bank credit is ₹4 less than `net_amount` due to an unlisted bank-side wire fee.
- **Duplicate-amount trap**: two unrelated settlements both net to exactly ₹12,340.00 on the same day — a deliberate ambiguity test.
- **Weekend clump**: Friday, Saturday, and Sunday settlements all credited together on the following Monday.

---

## 5. System Architecture

```
                ┌──────────────────────┐
                │   Data Generator      │  (Python) — produces the two CSVs
                │  + hidden answer key  │  + answer_key.json (never seen by matcher)
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   SQLite database     │  settlements, bank_statements,
                │                        │  matches, exceptions
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │  Matching Engine       │  Stage 1→5 pipeline (Section 6)
                │  (Python, pandas,      │
                │   rapidfuzz)           │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   FastAPI backend      │  REST endpoints (Section 10)
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   React dashboard      │  Summary view + Exception queue
                │                        │  (Section 11)
                └──────────────────────┘
```

**Components:**

1. **Data Generator** — Python script(s) producing seeded synthetic data with the true/exception/ambiguous split from Section 3.3, plus a hidden `answer_key.json` used only by the scoring script.
2. **Matching Engine** — the staged pipeline described in Section 6. Pure Python, no external service dependency except the final LLM tie-break stage.
3. **Exception Engine** — the confidence-tiering and reason-code logic described in Section 7, applied to whatever the matching engine could not close deterministically.
4. **Persistence** — SQLite (Section 9), chosen for zero-setup persistence appropriate to a prototype, with a clean upgrade path to Postgres if the project continues past the hackathon.
5. **API layer** — FastAPI, chosen to sit in the same language as the matching engine, avoiding a second service for a prototype timeline.
6. **Frontend** — React dashboard for the exception queue and summary reporting (Section 11).
7. **Telemetry (optional, lightweight)** — each stage emits a per-record result and a per-stage latency/volume counter, exposed as a simple JSON snapshot that feeds the per-stage funnel visualization. This needs no new infrastructure at prototype scale and doubles as the demo's throughput proof. Exporting the same counters to a production metrics server (Prometheus) is a future-scope upgrade (Section 17), not a prototype dependency.

---

## 6. Matching Engine — The Staged Pipeline

The core design principle: **never let one fuzzy blob of logic make the decision.** Each stage is a narrow, explainable rule; a record only reaches a later, less certain stage if the earlier ones could not close it with confidence.

**Stage 0 — Normalize**
Strip currency symbols and thousands separators, parse every date format into ISO 8601, uppercase text fields, convert every amount to an integer paise value, trim whitespace. Nothing downstream should ever compare raw, unnormalized strings.

**Stage 1 — Exact match**
Full UTR string found as a substring inside `description` or `ref_no`, AND `net_amount` matches the bank credit within ±₹1 (rounding tolerance). Confidence: 100.

**Stage 2 — Fuzzy UTR match**
Extract a UTR-like token from the freeform description via regex (a 12–18 character alphanumeric run). Compare it against the known UTR using edit-distance scoring (rapidfuzz), and separately test truncation-aware prefix/suffix matches (banks typically keep either the first N or last N characters). A candidate is only accepted if the amount also falls within tolerance. Confidence scales with edit distance and amount closeness.

**Stage 3 — Amount + date match (no usable UTR at all)**
When the description is empty or unparseable, search for settlement records whose `net_amount` matches the bank credit within a ±2 business-day window. If exactly one candidate exists, accept at medium confidence. If more than one settlement shares the same amount within the window, do **not** guess — this must be flagged as ambiguous and routed to the exception engine.

**Stage 4 — Batch-sum match (many-to-one)**
For a bank credit with no single matching settlement, search subsets of the remaining unmatched settlement pool whose `net_amount` values sum to the credit (±₹1), constrained to the date window. At this project's scale (50+ records, small unmatched pools per window) a bounded subset-sum dynamic-programming search is sufficient — no need for approximate or heuristic solvers. If exactly one valid partition exists, accept; if multiple valid partitions exist, flag as `BATCH_PARTITION_AMBIGUOUS`.

**Stage 5 — LLM tie-break (last resort only)**
For whatever remains unresolved after Stages 1–4, pass both candidate records' raw fields to an LLM (Google Gemini API) and request a plausibility judgment: which fields support a match, which contradict it, and a 0–100 confidence score. This is treated as one additional signal, never a sole authority — the LLM's score can move a borderline deterministic result into the review queue, but it cannot, by itself, auto-confirm a financial match. Every LLM-assisted decision retains the deterministic evidence trail alongside the LLM's stated reasoning, so a human reviewer sees both.

The call uses Gemini's structured output mode, forcing the response into a fixed JSON schema (`{match: bool, confidence: int, reasoning: string}`) rather than free text. This isn't an add-on — it's the difference between a parser that works and one that breaks the first time the model adds a pleasantry before the answer.

**Asynchronous LLM offloading (throughput protection)** — Because Stages 1–4 are deterministic and CPU-bound, they execute in milliseconds even across the full 50+ record batch. To keep that throughput, Stage 5 is deliberately decoupled from the synchronous path. Anything that needs LLM tie-breaking is pushed to an asynchronous background queue: the FastAPI endpoint returns the deterministically matched results immediately, and the dashboard shows a "Processing AI Tie-breaks…" indicator for the remaining edge cases. This keeps API rate limits and network latency from dragging down the primary reconciliation throughput.

---

## 7. Exception Engine — Confidence Tiers and Honest Routing

| Tier | Confidence | Rule | Action |
|---|---|---|---|
| Auto-match | ≥ 95 | Exact UTR + exact amount | Close automatically |
| Auto-match | 85–94 | Fuzzy UTR (edit distance ≤ 2) + amount within tolerance | Close automatically, log basis |
| Review queue | 60–84 | Amount+date match with a single candidate but no UTR corroboration; or a batch-sum match with exactly one valid partition | **Human Review Required** |
| Hard exception | < 60, or no candidate | Multiple equal-amount candidates, no candidate within the date window, amount mismatch beyond tolerance, unresolvable UTR | **Human Review Required**, high priority |

**Every exception record carries:**

- A reason code: `NO_CANDIDATE`, `MULTIPLE_CANDIDATES`, `AMOUNT_MISMATCH`, `UTR_UNRESOLVED`, `DATE_OUT_OF_WINDOW`, `BATCH_PARTITION_AMBIGUOUS`.
- The stage at which resolution failed.
- The top 1–3 closest candidates with their individual scores, so a human reviewer confirms or rejects rather than searching from scratch.

**7.1 Semantic exception clustering (review-fatigue reduction)** — Presenting a user with 50 isolated `NO_CANDIDATE` rows creates review fatigue. Before the Maker reviews, the engine groups hard exceptions into clusters sharing a root cause — normalized reason code plus lightweight string heuristics over the messy bank narration (prefix, token overlap, recurring fee-keyword match). These clusters surface as groups in the UI — *"These 32 exceptions share a recurring bank-fee pattern"* — so the Maker can apply a single resolution rationale to an entire cluster at once. This is the mechanism that powers the Bulk Select & Resolve action (Section 11). At this prototype's scale, reason-code plus string-feature clustering is sufficient and needs no new infrastructure. A vector-embedding store (e.g. ChromaDB) that clusters purely on semantic similarity is noted as a future upgrade (Section 17) once the corpus of distinct narration patterns grows beyond what string heuristics reliably separate.

**Final reporting requirement, non-negotiable:** the engine processes the entire batch — no pre-filtering, no cherry-picked subset. The report states:

```
match_rate     = auto_matched / total_records
review_rate    = review_queue / total_records
exception_rate = hard_exceptions / total_records
verified_rate  = records_closed / total_records   -- after Maker-Checker sign-off
```

alongside the full exception list. A lower, honestly-reported match rate is the intended outcome for a batch seeded with genuinely hard cases — a suspiciously perfect number is itself a red flag, and the write-up should say so plainly.

**A note on auto-match vs. closed books:** with the Maker-Checker workflow (Section 9–11) in place, the report must distinguish two different numbers. `match_rate` reflects the engine's own confidence — what it auto-identified. `verified_rate` reflects the state of the actual books — how many records have passed both maker AND checker and are truly closed. A record that is engine-confident but still sitting in `pending_approval` belongs to the first count, not the second. Reporting both shows the judge you understand that a reconciliation engine proposes; finance controls dispose.

---

## 8. Evaluation Methodology (Scoring Against the Hidden Answer Key)

A separate, offline scoring script — never invoked by the matching engine itself — compares the engine's output against `answer_key.json` and computes:

- **Precision** = true positives / (true positives + false positives)
- **Recall** = true positives / (true positives + false negatives)
- **Weighted accuracy score**, penalizing false positives at 3x the weight of false negatives (Section 3.3), reflecting that a wrongly-confirmed match is a worse operational outcome than an over-cautious exception.
- **Per-stage breakdown**: how many correct matches were closed at Stage 1 vs Stage 2 vs Stage 4 vs Stage 5 — useful both for the demo narrative and for identifying which stage is carrying the most weight.
- **Closed-vs-matched separation**: the scoring script reports auto-identified matches and verified-closed records as separate figures, so the demo can show both engine accuracy (matched) and books actually closed (passed Maker-Checker sign-off), making clear that pending-approval records are not yet treated as closed.

This scoring output is what should headline the demo: not "it matched things," but "it matched X% correctly, missed Y% cautiously, and got Z% wrong — here is exactly which records and why."

---

## 9. Database Schema (SQLite)

```sql
CREATE TABLE settlements (
    settlement_id       TEXT PRIMARY KEY,
    utr                  TEXT,
    settlement_date      TEXT,
    no_of_transactions   INTEGER,
    gross_amount         INTEGER,
    fees                 INTEGER,
    tax_gst              INTEGER,
    refunds_deducted     INTEGER,
    adjustments          INTEGER,
    net_amount           INTEGER,
    status               TEXT,
    bank_account_last4   TEXT
);

CREATE TABLE bank_statement (
    line_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_date      TEXT,
    value_date    TEXT,
    description   TEXT,
    ref_no        TEXT,
    debit         REAL,
    credit        REAL,
    balance       REAL,
    bank_name     TEXT
);

CREATE TABLE matches (
    match_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    settlement_id   TEXT,
    line_id         INTEGER,
    stage           TEXT,       -- e.g. 'exact', 'batch_sum'
    confidence      INTEGER,
    resolved_at     TEXT,
    FOREIGN KEY (settlement_id) REFERENCES settlements(settlement_id),
    FOREIGN KEY (line_id) REFERENCES bank_statement(line_id)
);

CREATE TABLE exceptions (
    exception_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    settlement_id    TEXT,
    line_id          INTEGER,
    reason_code      TEXT,
    confidence       INTEGER,
    candidates_json  TEXT,       -- top 1-3 ranked candidates, serialized
    status           TEXT,       -- append-only projection: 'open' / 'closed'
    created_at       TEXT
);
```

**9.1 Event-sourced audit log (immutability)** — In financial systems an audit trail isn't just a log; it's the ability to reconstruct the exact state of the books at any given second. Exceptions are never mutated in place to flip status. Instead, every action is an immutable event appended to `exception_events`, and an exception's current status is a projection derived by reading that log. Re-running the projection replays history faithfully; nothing can be silently overwritten.

```sql
CREATE TABLE exception_events (
    event_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    exception_id     INTEGER,
    event_type       TEXT,       -- 'CREATED', 'MAKER_PROPOSED', 'CHECKER_APPROVED', 'CHECKER_REJECTED'
    maker_id         TEXT,
    checker_id       TEXT,
    resolution_data  TEXT,       -- JSON payload of the action taken
    reason_text      TEXT,       -- free-text rationale
    timestamp        TEXT,
    FOREIGN KEY (exception_id) REFERENCES exceptions(exception_id)
);
```

The frontend reads the event log per exception to reconstruct its current state, giving a true, append-only financial audit trail. A summary row (`exceptions.status`) is kept only as an indexed denormalized cache for fast queue rendering; the event log is the system of record.

---

## 10. API Contract (FastAPI)

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/generate-data` | Trigger the synthetic data generator (seed both CSVs + hidden answer key) |
| `POST` | `/api/run-reconciliation` | Run the full staged matching pipeline against current data |
| `GET` | `/api/report` | Summary: match rate, review rate, exception rate, per-stage counts |
| `GET` | `/api/matches` | Full audit trail — every closed match with stage and confidence |
| `GET` | `/api/exceptions` | List of open exceptions with reason codes and ranked candidates |
| `POST` | `/api/exceptions/{id}/resolve` | **Maker** action: propose a resolution (confirm, reject, or manually override) — moves status to `pending_approval` |
| `POST` | `/api/exceptions/{id}/approve` | **Checker** action: senior controller signs off (approve) or rejects with reason — final closure |
| `GET` | `/api/exceptions/pending-approval` | Queue of maker-submitted resolutions awaiting checker sign-off |
| `GET` | `/api/settlements` | Raw settlement records (for the data-inspection view) |
| `GET` | `/api/bank-statement` | Raw bank statement records |
| `GET` | `/api/score` | (Demo/eval mode only) run the scoring script against the hidden answer key and return precision/recall |

---

## 11. Frontend — React Dashboard

- **Summary panel** — match rate / review rate / exception rate as headline numbers, plus a per-stage breakdown (how many matches closed at each stage).
- **Exception queue** — a table: reason code, confidence score, ranked candidates expandable per row. Supports **Bulk Select & Resolve** (checkbox column + "Apply Rule" button) so a finance user can batch-process identical exceptions (e.g. 20 records with the same `NO_CANDIDATE` reason) in one action. Individual actions: Confirm / Reject / Manual Override. All actions route through the **Maker-Checker** workflow: the initial action is a Maker (junior accountant) proposal, which moves the record to `pending_approval` status. A Checker (senior controller) must sign off before the exception is truly closed — visible as a separate "Pending Approval" tab in the queue.
- **Audit trail view** — every closed match, filterable by stage and confidence, so a reviewer can spot-check auto-matches, not just review exceptions.
- **Data inspection view** — raw settlement and bank statement tables, for demoing the "messiness" of the input data itself.

---

## 12. Tech Stack Summary

| Layer | Choice | Rationale |
|---|---|---|
| Matching engine | Python, pandas, rapidfuzz | pandas for tabular normalize/join logic; rapidfuzz for UTR edit-distance and fuzzy scoring |
| Batch-sum solver | Custom bounded subset-sum DP | Sufficient at this data scale, fully deterministic and explainable |
| LLM tie-break | Google Gemini API (free tier) | Used only as Stage 5 last resort, never a sole decision-maker |
| Backend/API | FastAPI | Same language as the matching engine — no separate service for a prototype timeline |
| Database | SQLite | Zero-setup, persistent, adequate for prototype scale; clean upgrade path to Postgres later |
| Frontend | React | Interactive exception queue with confirm/reject actions, not a static report |

---

## 13. Project Structure

```
recon-engine/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI entry point
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── schemas.py               # Pydantic request/response schemas
│   │   ├── db.py
│   │   ├── data_generator/
│   │   │   ├── generate_settlements.py
│   │   │   ├── generate_statement.py
│   │   │   ├── seed_config.py       # true/exception/ambiguous ratios
│   │   │   └── answer_key.py
│   │   └── matcher/
│   │       ├── normalize.py
│   │       ├── normalizer.py
│   │       ├── exact_match.py
│   │       ├── fuzzy_match.py
│   │       ├── amount_date_match.py
│   │       ├── batch_match.py
│   │       ├── llm_tiebreak.py
│   │       └── reconcile.py
│   ├── scoring/
│   │   └── score_against_answer_key.py
│   ├── data/                        # generated CSVs + answer_key.json live here
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── ExceptionQueue.jsx
│   │   │   └── AuditTrail.jsx
│   │   ├── components/
│   │   └── api/
│   └── package.json
└── docs/
    └── master-document.md            # this document
```

---

## 14. Build Plan (Priority-Ordered, Not Time-Boxed)

Given hackathon time pressure, prioritize by what's demoable at each checkpoint rather than a fixed hour count:

- **P0 — Must have for any demo**: data generator with hidden answer key; Stages 1–3 of the matching engine; basic exception list as JSON/console output; the headline match-rate/exception-rate numbers.
- **P1 — Core differentiator**: Stage 4 batch-sum matching; reason codes and ranked candidates on every exception; the scoring script against the answer key (precision/recall, not just a raw count).
- **P2 — Polish that wins**: React dashboard replacing console output; Stage 5 LLM tie-break with async offloading; Maker-Checker workflow with event-sourced audit log (Section 9.1) wired to the database.
- **P3 — Stretch, if time remains**: real-data texture layer (narration templates, realistic amount distributions); per-stage breakdown visualization; multi-bank-account scenario.

Build and demo P0 first, end to end, before adding anything from P1 — a working, honestly-scored full pipeline on the simplest cases beats a half-built version of every feature.

---

## 15. Risks and Known Limitations

- **Combinatorial growth in batch-sum matching** — subset-sum search must stay bounded (small candidate pools per date window); do not let it scan the entire unmatched dataset per bank line.
- **LLM API dependency** — Stage 5 depends on a free-tier external API; rate limits or downtime should degrade gracefully (fall back to Stage 4's result with a lower confidence label) rather than break the pipeline.
- **Synthetic data is a model of reality, not reality** — the write-up should be explicit that the messy-data patterns are seeded based on documented real-world failure modes, not scraped from an actual merchant account (which would raise its own privacy problems).
- **Scoring weight (3x on false positives) is a design choice, not a law** — state it explicitly in the demo so judges see it as a deliberate, defensible decision rather than an arbitrary number.
- **SQLite is a prototype choice** — fine for this scale and timeline; would need Postgres and proper migrations for anything beyond a demo.

---

## 16. Why This Wins (Track Alignment Recap)

The track brief warns explicitly against "one cherry-picked match" proving anything. Every design choice above is built to survive that scrutiny: the full batch is processed and reported on, the accuracy number comes from a hidden answer key rather than self-assessment, and the exception queue is a first-class feature with reason codes and ranked candidates — not a silent failure mode. That combination — throughput, a real measured number, and an honest exception list — is precisely the three-part bar the track sets.

---

## 17. Future Scope

These features are out of scope for the hackathon prototype but represent the natural product roadmap if ReconAgent were to become a production tool:

- **Cross-border payment reconciliation** — International payments introduce dynamic forex rates, currency conversion markups from intermediary banks, and SWIFT/reference codes instead of UTRs. Settlement amounts drift unpredictably between the gateway and the bank, requiring a new tolerance model built around exchange-rate windows rather than fixed paise thresholds.
- **Multi-currency support** — The current schema is INR-only (amounts in paise as integers). Extending to USD/EUR/GBP requires decimal-precision amounts, per-currency fee structures, and reconciliation rules that account for conversion spread.
- **Automated rule learning** — Instead of a fixed 5-stage pipeline, the engine could learn from confirmed human resolutions: "when the bank narration starts with `CMS001` and the amount matches within ₹10, auto-route to Stage 2." This converts the Maker-Checker audit trail into training data for the engine itself.
- **Continuous reconciliation (real-time)** — The prototype runs as a batch. Production use would poll for new settlement and bank-statement records on a schedule (e.g. every 15 minutes) and run the pipeline incrementally, only processing new or unresolved records.
- **TDS and GST line-item reconciliation** — Beyond matching settlement amounts, reconcile the tax components: did Razorpay deduct the correct GST on its fees? Does the TDS credit match the merchant's 194C/194J filing? This adds a second reconciliation axis beyond "did the money arrive."
- **Multi-bank account support** — Merchants operating across multiple bank accounts (e.g. separate accounts for UPI and card settlements) need a bank-account routing layer before matching, not just a `bank_account_last4` filter.
- **Vector-based exception clustering (ChromaDB)** — The prototype clusters hard exceptions with reason-code plus string heuristics (Section 7.1), which is sufficient at 50 records. As the corpus of distinct bank-narration patterns grows, a local vector store (ChromaDB) can cluster purely on semantic similarity of descriptions, letting one rationale clear a batch of superficially different but same-root-cause exceptions.
- **Production metrics export (Prometheus)** — The prototype exposes lightweight per-stage latency/volume counters as a JSON snapshot (Section 5). Exporting the same counters to Prometheus, with dashboards for `recon_stage_latency_seconds` and `recon_stage_resolution_total`, becomes worthwhile in production to prove throughput and visualize the match funnel continuously rather than post-run.
