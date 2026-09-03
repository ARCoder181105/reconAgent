# ReconAgent — Product Requirements Document (PRD)

Project codename: **ReconAgent**
Track: Razorpay Buildathon, Track 04 — AI Finance Controller
Author of record: the human maintainer (single-owner project)
Ultimate source of truth: [`master-design.md`](./master-design.md)

---

## 1. Problem Statement

Finance teams reconcile payment-gateway settlement reports against bank statements largely by hand — a VLOOKUP-on-UTR exercise in Excel with no confidence score, no record of *why* a match was accepted, and a tendency to silently skip and forget ambiguous cases. The 2026 builder consensus is that verification capacity, not generation speed, is the bottleneck.

ReconAgent automates the reconciliation loop across a 50+ record synthetic batch, reports a **measured** match rate, and surfaces an **honest** exception list for whatever it cannot confidently resolve.

## 2. Goals

| Goal | Success measure |
|---|---|
| Throughput | Full 50+ record batch processed in one run, no manual pre-filtering |
| Measured accuracy | Real precision/recall from a hidden synthetic answer key, not self-assessment |
| Honest exception list | Every unresolved record gets reason code + confidence + ranked candidates; never silently dropped |
| Production-grade guardrails | Maker-Checker workflow + event-sourced, append-only audit log |

## 3. Non-Goals

Explicitly **out of scope** (see [`scope.md`](./scope.md) for the full list):

- Cross-border payment reconciliation (forex drift, SWIFT refs)
- Multi-currency support (INR/paise only)
- Vector-based (ChromaDB) semantic clustering — lightweight string heuristics only
- Prometheus/metrics-server telemetry — lightweight JSON counters only
- Real-time / continuous reconciliation — batch only
- Multi-bank-account routing layer
- Real merchant data — synthetic ground-truth data only

## 4. Users / Personas

| Persona | Needs |
|---|---|
| **Maker** (junior accountant) | Batch exceptions, propose resolutions quickly, clear clusters of related records |
| **Checker** (senior controller) | Review maker proposals, sign off / reject with reason, immutable audit trail |
| **Engine (automated)** | Close every match it can with confidence; escalate everything it cannot |

## 5. Core User Flows

1. **Generate data** — POST `/api/generate-data` seeds both CSVs + hidden answer key.
2. **Run reconciliation** — POST `/api/run-reconciliation` runs Stages 1–5, returns deterministic matches sync, queues LLM tie-breaks async.
3. **Review exceptions** — Maker opens queue, sees clustered/grouped hard exceptions, Bulk Select & Resolve or per-row action.
4. **Approve** — Checker opens Pending Approval tab, signs off or rejects.
5. **Measure** — GET `/api/report` + GET `/api/score` (eval mode only) report match/verified rates + precision/recall.

## 6. Success Criteria (Track Alignment)

The track warns against "one cherry-picked match." ReconAgent survives that scrutiny because it reports the whole batch, a real measured number, and a first-class exception queue. A lower, honest match rate on a batch seeded with hard cases is the *intended* outcome.

## 7. Dependencies

- Google Gemini API (free tier) — Stage 5 only, async, must degrade gracefully
- SQLite (zero setup, prototype choice)
- No public row-level merchant dataset exists — synthetic data is the backbone (see [`data-sources.md`](./data-sources.md))
