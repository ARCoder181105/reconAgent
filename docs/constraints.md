# ReconAgent — Constraints

> Hard limits every agent must respect. If a constraint blocks work, record it — do not silently violate it.

## Non-Negotiable (from `master-design.md`)

| Constraint | Detail |
|---|---|
| Process whole batch | Must run the full 50+ record batch; no pre-filtering, no cherry-picked subset |
| Measured accuracy | Score against hidden `answer_key.json`; never self-assess |
| Honest exception list | Every unresolved record gets reason code + confidence + ranked candidates; never silently dropped |
| FP penalized 3x | False positives weigh 3x false negatives in scoring (decisions.md D7) |
| Event-sourced exceptions | Never `UPDATE` exception status in place — append events only (decisions.md D2) |
| LLM is last resort | Stage 5 only, async, structured output, never sole authority (decisions.md D5) |
| Maker-Checker | Maker proposes; only Checker closes books (decisions.md D6) |

## Tooling / Environment

- **Gemini API (free tier)**: rate limits + latency. Stage 5 must be async and degrade gracefully — if the API fails, fall back to Stage 4's result with a lower-confidence label, never break the pipeline.
- **SQLite**: single-writer, prototype scale. Not for concurrent heavy writes; adequate for 50+ records.
- **Subset-sum explosion**: batch-sum search must stay bounded to small candidate pools per date window. Never scan the entire unmatched dataset per bank line.

## Data

- **No real row-level financial data.** Synthetic only. Explicitly flag the write-up: messy-data patterns are seeded from documented real-world failure modes, not scraped from an actual merchant account.
- **INR / integer-paise only.** No multi-currency.
- **Hidden answer key**: generate alongside data but keep out of matcher scope (see `data-sources.md`).

## Scoring Weights Are a Choice

The 3x FP weight is a deliberate, defensible design decision, not a law. State it explicitly in the demo so judges see it as intentional.

## Scope

Respect `scope.md` — ChromaDB, Prometheus, cross-border, multi-currency, real-time, and multi-bank routing are all out of scope for the prototype.
