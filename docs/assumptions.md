# ReconAgent — Assumptions

> Explicit assumptions made during design. **Flagged for human review — not silently baked in.** All derive from `master-design.md` unless confidence is stated otherwise. If any is wrong, update it here and in `master-design.md`, then `changelog.md`.

## Data & Domain

| # | Assumption | Confidence | Needs human review? |
|---|---|---|---|
| A1 | Synthetic-only data is acceptable for the track (no real row-level merchant data required). | High | Yes — confirm no real-data expectation from judges. |
| A2 | 70/20/10 (true/exception/ambiguous) ratio is a reasonable real-world mix. | Medium | Yes — tunable in `seed_config.py`. |
| A3 | INR / integer-paise only is within track expectations. | High | No. |
| A4 | Real-world UTR is typically 12–18 alphanumeric chars and banks keep either first-N or last-N when truncating. | Medium | Yes — drives Stage 2 heuristics. |
| A5 | MDR ~2% + 18% GST is a representative Razorpay fee model. | High | No — used as default in generator. |

## Architecture & Tooling

| # | Assumption | Confidence | Needs human review? |
|---|---|---|---|
| A6 | Bounded subset-sum DP is efficient enough at 50+ records (small pools per date window). | High | No — but monitor growth (constraints.md). |
| A7 | Async background queue + polling is sufficient; no message broker (Redis/Kafka) needed. | High | Yes — if batch grows, broker may be needed. |
| A8 | ChromaDB and Prometheus are genuinely unnecessary at this scale; string heuristics + JSON counters suffice. | Medium | Yes — this is the "event source + async only" scope decision. |
| A9 | SQLite handles prototype concurrency (single Maker + single Checker + engine). | High | Yes — if multi-user load is expected post-hackathon, note Postgres. |
| A10 | Free-tier Gemini latency/rate-limit is tolerable given async offload. | Medium | Yes — need fallback behavior defined (constraints.md). |

## Scoring

| # | Assumption | Confidence | Needs human review? |
|---|---|---|---|
| A11 | 3x false-positive penalty is the right default. | Medium | Yes — deliberate judgment call; must be stated in demo. |
| A12 | `verified_rate` (post-Maker-Checker) is a metric judges value. | Medium | Yes — product/domain call. |

## Product

| # | Assumption | Confidence | Needs human review? |
|---|---|---|---|
| A13 | A Maker + Checker (two-role) workflow, not one role, is the right controls model for the demo. | Medium | Yes — domain flex; confirm it reads as deliberate, not complexity. |
| A14 | Single human owner; "ownership.md" is workflow phases, not multi-person division. | High | No — stated by owner. |

## Status

None of the above have been ratified by the human yet. Once you review and accept an assumption, move its "Needs human review?" to "No" and note ratification in `review-log.md`.
