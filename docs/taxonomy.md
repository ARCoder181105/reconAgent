# ReconAgent — Taxonomy

> Confidence tiers, exception reason codes, status/event vocabulary. Locked. Source: `master-design.md` §7, §9.

## Confidence Tiers

| Tier | Confidence | Rule | Action |
|---|---|---|---|
| Auto-match | ≥ 95 | Exact UTR + exact amount | Close automatically |
| Auto-match | 85–94 | Fuzzy UTR (edit distance ≤ 2) + amount in tolerance | Close automatically, log basis |
| Review queue | 60–84 | Amount+date single candidate, no UTR corrob; or batch-sum with exactly one valid partition | Human Review Required (Maker) |
| Hard exception | < 60, or no candidate | Multiple equal-amount candidates, no candidate in date window, amount mismatch beyond tolerance, unresolvable UTR | Human Review Required, high priority |

## Exception Reason Codes (canonical, single vocabulary)

| Code | Meaning |
|---|---|
| `NO_CANDIDATE` | No settlement candidate found at all |
| `MULTIPLE_CANDIDATES` | More than one plausible candidate, cannot decide (e.g. duplicate-amount trap) |
| `AMOUNT_MISMATCH` | Candidate found but amount outside tolerance |
| `UTR_UNRESOLVED` | UTR too garbled/truncated to resolve |
| `DATE_OUT_OF_WINDOW` | No candidate within the acceptable date window |
| `BATCH_PARTITION_AMBIGUOUS` | Multiple valid subset-sum partitions for a batch credit |

## Pipeline Stage Identifiers

| Stage | Key (used in matches.stage) |
|---|---|
| 1 | `stage1_exact` |
| 2 | `stage2_fuzzy_utr` |
| 3 | `stage3_amount_date` |
| 4 | `stage4_batch_sum` |
| 5 | `stage5_llm_tiebreak` |

## Event Types (event-sourced audit log)

| Event | Meaning | Appended by |
|---|---|---|
| `CREATED` | Exception entered the queue | Engine |
| `MAKER_PROPOSED` | Maker proposed a resolution (confirm/reject/override) | Maker |
| `CHECKER_APPROVED` | Checker signed off — exception closed | Checker |
| `CHECKER_REJECTED` | Checker rejected maker's proposal, with reason | Checker |

## Exception Status (projection, derived from events)

| Status | Meaning |
|---|---|
| `open` | No proposal yet, or pending a final decision |
| `closed` | Checker approved — final, immutable |
| (derived) `pending_approval` | Maker proposed, awaiting Checker — surfaced in the Pending Approval tab |

## Match-Rate Vocabulary (metrics)

```
match_rate     = auto_matched / total_records      (engine confidence)
review_rate    = review_queue / total_records
exception_rate = hard_exceptions / total_records
verified_rate  = records_closed / total_records    (after Maker-Checker sign-off)
```

`match_rate` and `verified_rate` differ: the former is engine confidence, the latter is books actually closed. Reporting both is mandatory (decisions.md D6).

## Anti-Patterns

- Do not invent new reason codes ad hoc — reuse the canonical list above.
- Do not map `pending_approval` to a mutable column; it is a derived projection from `CHECKER_APPROVED`/`MAKER_PROPOSED` events.
- Do not treat `match_rate` as "books closed."
