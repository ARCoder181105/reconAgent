# ReconAgent — Tech Stack

> Locked stack from `master-design.md` §12. Versions are the ones in use; pin exact versions in `requirements.txt` / `package.json` at implementation time.

## Backend / Matching Engine

| Layer | Choice | Version | Why |
|---|---|---|---|
| Language | Python | 3.11+ | Same language for matcher + API; no two-language split |
| Data / tabular | pandas | 2.x | Table normalize/join logic, CSV handling |
| Fuzzy matching | rapidfuzz | 3.x | UTR edit-distance + truncation-aware scoring (fast C impl, no Levenshtein package) |
| Batch-sum | custom DP | n/a | Bounded subset-sum; deterministic + explainable at this scale |

## LLM (Stage 5 only)

| Layer | Choice | Version | Why |
|---|---|---|---|
| Provider | Google Gemini / Local Ollama | free tier / local | Hackathon-accessible, JSON schema support via structured output. Ollama supported as a local alternative. |
| Structured output | Gemini `json` mode / Ollama `format=json` | SDK latest | Forces fixed `{match, confidence, reasoning}` schema — no chatty text to break the parser |
| Execution | async background queue | n/a | Decoupled so Stages 1–4 stay at millisecond throughput (D5) |

## Backend / API

| Layer | Choice | Version | Why |
|---|---|---|---|
| Web framework | FastAPI | 0.1xx | Same language as matcher, built-in OpenAPI, async support for queue integration |
| ORM | SQLAlchemy | 2.x | Maps the event-sourced tables to the SQLite schema |
| Validation | Pydantic | 2.x | Request/response validation, structured-output parsing |

## Database

| Layer | Choice | Version | Why |
|---|---|---|---|
| RDBMS | SQLite | bundled/stdlib | Zero setup, persistent, adequate for prototype; Postgres upgrade path |

## Frontend

| Layer | Choice | Version | Why |
|---|---|---|---|
| Framework | React | 18.x | Interactive exception queue, not static report |
| Build tool | Vite | 5.x | Fast dev, simple React SPA |
| HTTP | fetch / axios | latest | Talk to FastAPI; polling for async tie-break status |

## Explicitly NOT in the core stack (see SCOPE.md)

- **ChromaDB** — excluded. Exception clustering uses reason code + string heuristics.
- **Prometheus** — excluded. Telemetry is lightweight JSON counters, not a metrics server.
- **Postgres** — excluded. Future upgrade only.
- **Additional ML/NLP libs** — excluded. Keep the pipeline deterministic except Stage 5.

---

## Decision Record

| Choice | Linked decision |
|---|---|
| FastAPI same-language backend | decisions.md D4 |
| Async LLM | decisions.md D5 |
| SQLite + event sourcing | decisions.md D2 |
| rapidfuzz | Stage 2 (fuzzy UTR) |
| pandas | Stage 0 normalize + tabular joins |
