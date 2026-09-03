# ReconAgent — Data Sources & Synthetic Ground Truth

> How the synthetic data generator works, the true/exception ratio, and how the hidden answer key is used for scoring. Source: `master-design.md` §3.

## Why Synthetic, Not Real

No public dataset pairs a payment-gateway settlement report with a matching bank statement at merchant-record level with a known correct answer — that pairing is private financial data. Public "settlement data" datasets are aggregate system-wide stats, not row-level merchant records, and carry no ground-truth pairing.

The track's quality bar demands **measured** accuracy, which requires already knowing the correct answer for each record. Only synthetic data with a hidden answer key makes real precision/recall possible.

## How The Generator Works

The generator produces two CSVs **plus** a hidden `answer_key.json`. The answer key is generated alongside the messy data but withheld from the matching pipeline.

### Inputs (seeded, deterministic)

- True/exception/ambiguous ratios (see below)
- Real-world messy-data patterns: truncated UTRs, bundled batch credits, missing descriptions, mid-string UTRs, off-by-fee amounts, duplicate-amount traps, weekend clumps

### Outputs

1. `settlements.csv` — structured side (`setl_` ids, full UTR, net computation from gross − fees − GST − refunds + adjustments)
2. `bank_statement.csv` — messy side (inconsistent dates, freetext descriptions, garbled ref_no, debit/credit, balance noise, bank name)
3. `answer_key.json` — the ground-truth settlement↔bank-line mapping + the genuine orphans (used ONLY by the offline scoring script)

### The Answer-Key Composition

| Category | Share | Description |
|---|---|---|
| **True matches** | ~70% | Correct settlement-to-bank pairs, spread across difficulty (exact-UTR easy, fuzzy/truncated-UTR medium, batched-credit hard) |
| **True exceptions** | ~20% | Deliberately unmatchable: orphan bank charges, not-yet-credited settlements, duplicate-amount traps with no correct answer |
| **Ambiguous-but-resolvable** | ~10% | Matchable only with real work: batch-sum split across 2–4 settlements, high-edit-distance fuzzy UTR |

## Messy-Data Examples Seeded Deliberately

- **Truncated UTR**: `NEFT-1597813219E1P-RAZORPAY SOFTWARE PVT LTD`
- **Bundled/batched credit**: one bank line = sum of 3 settlements, nothing in description indicates it
- **Missing description**: `BY TRANSFER-CLG`, blank `ref_no` — forces pure amount+date match
- **Mid-string UTR**: `CMS001/RZRPY/1597813219E1PQ6W/BATCH`
- **Off-by-fee amount**: bank credit ₹4 less than net due to unlisted bank wire fee
- **Duplicate-amount trap**: two unrelated settlements both ₹12,340.00 same day
- **Weekend clump**: Fri/Sat/Sun settlements all credited Monday

## Where Real Data Adds Value (Texture Only)

- Narration string patterns from public Indian bank datasets → applied as templates over synthetic rows (original labels/columns discarded)
- Real e-commerce order-value distribution → drives underlying amounts (₹149, ₹899, ₹2,499 clustering)
- RBI system-wide stats → one color line in the pitch, not row-level data

## Scoring (Uses the Hidden Answer Key)

The offline scoring script (never invoked by the engine) computes:

- **Precision** = TP / (TP + FP)
- **Recall** = TP / (TP + FN)
- **Weighted accuracy** — FP penalized 3x FN (decisions.md D7)
- **Per-stage breakdown** — matches closed at Stage 1 vs 2 vs 4 vs 5
- **Closed-vs-matched separation** — auto-identified vs Maker-Checker verified-closed

## Hard Constraint

The generator MUST NOT leak `answer_key.json` into matcher scope. The matcher sees only the two CSVs. Answer key lives in `data/`, consumed only by `scoring/score_against_answer_key.py`.
