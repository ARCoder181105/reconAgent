# ReconAgent — Locked Decisions

> **Binding.** Agents MUST obey these decisions. Do not re-litigate. If a contradiction appears, `sources-of-truth.md` resolves it.

These decisions are locked from the design in `master-design.md`. Each entry states the decision and the rationale; if you believe one must change, record it as new work and get human approval — do not silently deviate.

---

## D1 — 5-Stage Matching Pipeline
The engine is a staged, narrow-explainable-rule pipeline, not one fuzzy blob:
- **Stage 0** Normalize (currency, dates→ISO, uppercase, paise ints)
- **Stage 1** Exact UTR substring + amount
- **Stage 2** Fuzzy UTR (rapidfuzz edit-distance, truncation-aware)
- **Stage 3** Amount + date window (refuses on multi-candidate ambiguity)
- **Stage 4** Batch-sum (many-to-one) bounded subset-sum DP
- **Stage 5** LLM tie-break (last resort, see D5)

Rationale: throughput + explainability. A record only advances to a less-certain stage if earlier ones cannot close it.

## D2 — SQLite + Event-Sourced Exception Log
Persistence is SQLite. Exceptions are **never mutated in place**; every action is an immutable append-only event (`exception_events`), and status is a projection. See D7.

Rationale: zero-setup prototype persistence with a clean Postgres upgrade path; immutable financial audit trail.

## D3 — Synthetic Ground Truth With Hidden Answer Key
No real row-level merchant data. A generator produces both CSVs **plus** a hidden `answer_key.json` used only by the offline scoring script.
True matches ~70% / true exceptions ~20% / ambiguous-but-resolvable ~10%.

Rationale: only a hidden answer key enables real precision/recall scoring.

## D4 — FastAPI Backend, Same Language As Matcher
Backend API is FastAPI (Python), same language as the matching engine. No second service for a prototype timeline.

## D5 — Asynchronous LLM Tie-Break (Google Gemini)
Stage 5 is decoupled onto an async background queue. The endpoint returns deterministic results immediately. Gemini used **only** with structured output mode (fixed JSON schema). LLM is one signal, never sole authority — it cannot auto-confirm a financial match.

Rationale: protects Stage 1–4 millisecond throughput from API latency/rate limits; guarantees parsable JSON.

## D6 — Maker-Checker Workflow
A financial exception is rarely resolved by one person. The **Maker** proposes (confirm/reject/override) — record goes to `pending_approval`. The **Checker** signs off or rejects with reason. Books close only after checker approval. Metrics distinguish `match_rate` (engine) from `verified_rate` (closed books).

## D7 — Weighted Accuracy, False Positives Penalized 3x
Scoring penalizes false positives at 3x false negatives (configurable, default caution). A wrongly-confirmed match is a financial-control failure; an over-cautious exception is a minor inconvenience.

## D8 — Reports Expose Confusion Matrix + Per-Stage Breakdown
Scoring outputs precision, recall, weighted accuracy, and per-stage counts (how many closed at Stage 1 vs 2 vs 4 vs 5). Headline = the honest numbers, not "it matched things."

---

## Re-Litigation Policy

To change a locked decision: open a task in `tasks.md`/`backlog.md`, write the proposed change with impact, get human approval, then update `master-design.md`, `decisions.md`, and `changelog.md`. Locked means locked until that process runs.
