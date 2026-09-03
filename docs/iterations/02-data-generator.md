# Iteration 02 — Data Generator + Hidden Answer Key

> Phase P0. (Depends on 01.)

## Goal

Produce `settlements.csv`, `bank_statement.csv`, and hidden `answer_key.json` with the 70/20/10 split and all deliberate messiness patterns from `master-design.md` §3, §4. ≥50 records. Deterministic output with a fixed seed.

## Files

- `backend/app/data_generator/__init__.py`
- `backend/app/data_generator/seed_config.py` — ratios, seed, record count, tunables
- `backend/app/data_generator/generate_settlements.py` — `settlements.csv`
- `backend/app/data_generator/generate_statement.py` — `bank_statement.csv`
- `backend/app/data_generator/answer_key_generator.py` — `answer_key.json`
- `backend/data/.gitkeep` (already present)

## Data Shapes (see §4)

**`settlements.csv`**: `settlement_id` (`setl_...`), `utr` (full), `settlement_date`, `no_of_transactions`, `gross_amount`, `fees`, `tax_gst`, `refunds_deducted`, `adjustments`, `net_amount`, `status`, `bank_account_last4`. All amounts paise ints. `net_amount = gross − fees − tax − refunds + adjustments`.

**`bank_statement.csv`**: `txn_date` (mixed formats), `value_date`, `description` (freetext), `ref_no`, `debit`, `credit`, `balance`, `bank_name`.

## Messiness Patterns to Seed (§4.3)

- Truncated UTR (`NEFT-1597813219E1P-...`)
- Bundled/batched credit (one bank line = sum of 3 settlements)
- Missing description (`BY TRANSFER-CLG`, blank `ref_no`)
- Mid-string UTR (`CMS001/RZRPY/<UTR>/BATCH`)
- Off-by-fee amount (bank credit ₹4 less than net)
- Duplicate-amount trap (two settlements both ₹12,340.00 same day)
- Weekend clump (Fri/Sat/Sun credits land Monday)

## Composition (from §3.3)

- ~70% true matches (across difficulty bands)
- ~20% true exceptions (orphans, not-credited, duplicate traps)
- ~10% ambiguous-but-resolvable (batch-sum, high-edit-distance UTR)

## Key Notes

- **Hidden answer key is HARD-guarded**: recorded true settlement↔line mappings + genuine orphans. Generate alongside the CSVs but keep gated so the matcher can never import or read it. Only the offline scoring script (06) consumes it.
- Deterministic seed in `seed_config.py` so the same batch regenerates.
- Do not rely on system time in generation (except controlled date offsets).

## Tests

- File exists with ≥50 settlement rows and matching bank rows.
- `net_amount` arithmetic holds for every settlement row.
- Answer key is internally consistent (every key references existing ids; orphans listed).
- Answer key is NOT discoverable/importable from the matcher package path.

## Exit Criteria

- Regeneration is reproducible (same seed → same files).
- Composition ratios land near target (within tolerance) so scoring is meaningful.

## Commit

`feat(data): add seeded generator with hidden answer key`
