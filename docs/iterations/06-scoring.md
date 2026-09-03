# Iteration 06 — Scoring Against Hidden Answer Key

> Phase P1. (Depends on 05.)

## Goal

Offline scoring script computing precision/recall, weighted accuracy (3x on false positives), per-stage breakdown, and closed-vs-matched separation, compared against `answer_key.json`.

## Files

- `backend/scoring/__init__.py`
- `backend/scoring/score_against_answer_key.py`

## Behavior

Reads: the generated CSVs, `answer_key.json`, and the persisted `Match`/`Exception` state. Computes:

- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **Weighted accuracy**, FP penalized 3x FN (decisions.md D7) — configurable, default caution
- **Per-stage breakdown**: matches closed at `exact` vs `fuzzy_utr` vs `amount_date` vs `batch_sum`
- **Closed-vs-matched separation**: auto-identified (`match_rate`) vs Maker-Checker verified-closed (`verified_rate`)

Output a clear JSON/console report that can headline the demo:
> "matched X% correctly, missed Y% cautiously, got Z% wrong — here is exactly which records and why."

## Key Notes

- **NEVER imported by the engine** — runs offline only (boundary from `architecture.md`, `constraints.md`).
- It is the ONLY consumer of `answer_key.json`.
- Group output by record so a reviewer can trace each decision.

## Tests

- On a fixed generated batch, metrics in [0,1].
- Inject a known false positive and a false negative; verify FP weighs 3x FN in the weighted score.
- Per-stage counts sum to total true positives.

## Exit Criteria

- Measured accuracy available and reproducible.
- Baseline numbers are honest (a perfect score on a hard-seeded batch is a red flag, not a goal).

## Commit

`test: add precision/recall scoring against hidden answer key`
