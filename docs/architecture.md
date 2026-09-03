# ReconAgent — Architecture

> System components, data flow, boundaries. Source: `master-design.md` §5.

```
┌──────────────────────┐
│   Data Generator      │  (Python) — produces 2 CSVs + hidden answer_key.json
│  + hidden answer key  │  (never seen by matcher)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   SQLite database     │  settlements, bank_statements, matches,
│                        │  exceptions, exception_events (event-sourced)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│  Matching Engine       │  Stage 0→5 pipeline
│  (Python)              │  deterministic; Stage 5 async LLM offload
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   FastAPI backend      │  REST endpoints (maker/checker/measurement)
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│   React dashboard      │  Summary + Exception queue (bulk resolve,
│   (Maker/Checker UI)  │   Maker-Checker, audit trail)
└──────────────────────┘
```

## Components

1. **Data Generator** — seeded synthetic data with true/exception/ambiguous split (70/20/10) plus hidden `answer_key.json` used only by the offline scoring script.
2. **Matching Engine** — staged pipeline (decisions.md D1). Pure Python; only external service is the Stage 5 LLM.
3. **Exception Engine** — confidence-tiering + reason-code + lightweight semantic clustering (reason code + string heuristics). Applies to whatever Stages 1–4 could not close deterministically.
4. **Persistence** — SQLite. Exceptions are event-sourced: `exception_events` is append-only, `exceptions.status` is a denormalized projection for fast queue rendering. The event log is the system of record.
5. **API layer** — FastAPI. Maker/Checker/measurement endpoints.
6. **Frontend** — React dashboard.

## Data Flow (run-reconciliation)

1. Client `POST /api/run-reconciliation`
2. Engine normalizes + runs Stages 1–4 **synchronously** → writes `matches`
3. Unresolved records → routed to exception engine → written as `CREATED` events with reason codes + ranked candidates
4. LLM-needed cases pushed to **async queue** → results append events
5. Response returns immediately with deterministic match set + "Processing AI Tie-breaks…" status
6. Maker/Checker resolve via event-sourced workflow

## Boundaries / Isolation

| Boundary | Don't cross |
|---|---|
| Data generator vs matcher | Generator must not leak `answer_key.json` into matcher scope |
| Matcher vs scorer | Scoring script is offline, never invoked by engine |
| Deterministic stages vs LLM | LLM (Stage 5) is last-resort, async, never sole authority |
| Maker vs Checker | Maker can't close books; only Checker approves closure |
| Writes to exceptions | Never `UPDATE` status in place — always append an event |

## The 3 Work Clusters

Mapped in `ownership.md`. Single-owner project, but splits the build by concern:
- **Cluster A: Data Gen & Scoring**
- **Cluster B: Backend Matcher & API**
- **Cluster C: React Dashboard & Maker-Checker UI**
