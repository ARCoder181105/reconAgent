# Iteration 03 — Normalize + Exact + Fuzzy UTR Matching

> Phase P0. (Depends on 02.)

## Goal

First three pipeline units: `normalizer` (Stage 0), `exact_match` (Stage 1), `fuzzy_match` (Stage 2). Each is a narrow, explainable rule reading normalized data.

## Files

- `backend/app/matcher/__init__.py`
- `backend/app/matcher/normalizer.py`
- `backend/app/matcher/exact_match.py`
- `backend/app/matcher/fuzzy_match.py`
- `backend/app/matcher/__shared__.py` — amount tolerance, UTR-token extraction, date-window helpers (used across stages)

## Behavior

**`normalizer.py` (Stage 0)**
- Strip currency symbols + thousands separators
- Parse every date format → ISO `YYYY-MM-DD`
- Uppercase text fields
- Convert amounts to integer paise
- Trim whitespace

Nothing downstream compares raw, unnormalized strings.

**`exact_match.py` (Stage 1)**
- Full UTR found as a substring inside `description` OR `ref_no`
- AND `net_amount` matches bank credit within ±₹1 (rounding tolerance)
- Confidence: 100

**`fuzzy_match.py` (Stage 2)**
- Extract a UTR-like token (12–18 char alphanumeric run) from freeform description via regex
- Compare against known UTR with rapidfuzz edit-distance scoring
- Truncation-aware: test prefix/suffix matches (banks keep first-N or last-N)
- Only accept if amount also within tolerance
- Confidence scales with edit distance + amount closeness

## Tests

- `exact_match`: clean UTR substring → confidence 100.
- `fuzzy_match`: truncated UTR and mid-string UTR resolve; a wrong-amount candidate is rejected.
- `normalizer`: mixed date formats + currency → canonical form.
- Determine each stage's inputs/outputs (settlement candidate + score + pass/fail).

## Exit Criteria

- Known cells produce expected results (exact high conf, fuzzy medium conf, amount-guard rejects).
- No raw string/amount comparisons left in these modules.

## Commit

`feat(matcher): add normalize, exact and fuzzy UTR matching`
