# Iteration 00 — Docs Alignment (Semantic Naming + Filenames)

> A one-time up-front docs pass so the specs match the implementation naming before any code lands. Do this before Iteration 01.

## Goal

Align `taxonomy.md` and `master-design.md` to the locked naming convention so code never contradicts the spec while we build.

## Files

- `docs/taxonomy.md`
- `docs/master-design.md`
- `docs/data-sources.md` (filename references)
- `docs/iterations/README.md` (already reflects the convention)

## Changes

1. **`taxonomy.md` — stage-key table**: replace `stage1_exact` / `stage2_fuzzy_utr` / `stage3_amount_date` / `stage4_batch_sum` / `stage5_llm_tiebreak` with the semantic keys `exact` / `fuzzy_utr` / `amount_date` / `batch_sum` / `llm_tiebreak`.
2. **`master-design.md` — pipeline §6**: update stage headings and the `matches.stage` example comment to semantic names; rename `pipeline.py` reference to `reconcile.py`.
3. **`master-design.md` / `data-sources.md` — filenames**: `razorpay_settlements.csv` → `settlements.csv`; generator references → `generate_settlements.py` / `generate_statement.py`.
4. Keep "Razorpay" only in pitch/UI/branding copy, not internal identifiers.

## Notes

- Reason codes, event types, confidence tiers, endpoints, and ORM model names are NOT renamed — they are already clean and locked.
- Do not touch behavior; this is a rename-only alignment.

## Tests

- None (docs-only). Run a grep to confirm no stale `stage1_` / `razorpay_settlements` references remain in `docs/` except where "Razorpay" is used as branding.

## Exit Criteria

- No stale `stageN_*` or `razorpay_settlements.csv` identifiers in specs.
- `taxonomy.md` stage keys match the values the code will write into `matches.stage`.

## Commit

`docs: align stage naming and filenames to implementation`
