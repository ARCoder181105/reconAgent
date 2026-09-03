# Iteration 04 — Amount/Date + Batch-Sum Matching

> Phase P0/P1. (Depends on 03.)

## Goal

`amount_date_match` (Stage 3) and `batch_match` (Stage 4, many-to-one batch-sum). Both deterministic and explainable.

## Files

- `backend/app/matcher/amount_date_match.py`
- `backend/app/matcher/batch_match.py` (+ extend `__shared__.py` if needed)

## Behavior

**`amount_date_match.py` (Stage 3)** — no usable UTR at all
- Search settlement records whose `net_amount` matches bank credit within a ±2 business-day window.
- Exactly one candidate → accept at medium confidence.
- More than one settlement with same amount in window → **do NOT guess**; route as ambiguous (`MULTIPLE_CANDIDATES`). The flag lands in 05.

**`batch_match.py` (Stage 4)** — many-to-one
- For a bank credit with no single matching settlement: search subsets of remaining unmatched settlements whose `net_amount` values sum to the credit (±₹1), constrained to the date window.
- Bounded subset-sum via DP. Do NOT scan the whole dataset per bank line (see `constraints.md`).
- Exactly one valid partition → accept.
- Multiple valid partitions → `BATCH_PARTITION_AMBIGUOUS`.

## Key Notes

- Keep candidate pools small (bounded by date window) — enforcement of the combinatorial risk guard.
- Business-day window helper lives in `__shared__.py`.

## Tests

- `amount_date_match`: single candidate accepts; duplicate-amount window → ambiguity, no guess.
- `batch_match`: an exact partition resolves; a multi-partition case flags `BATCH_PARTITION_AMBIGUOUS`.
- Subset-sum returns the single deterministic partition when unique.

## Exit Criteria

- Both units pass their known cases.
- No unbounded full-dataset scan in `batch_match`.

## Commit

`feat(matcher): add amount-date and batch-sum matching`
