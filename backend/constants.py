"""Backend-wide constants shared across sub-packages.

These are the canonical values that more than one folder in ``backend/`` rely
on — most importantly the default LLM model (previously hardcoded in
``config.py``) and the domain vocabulary locked in ``docs/taxonomy.md``.
"""
from __future__ import annotations

# --- Default LLM model for Stage 5 (overridable via GEMINI_MODEL env) ---
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"

# --- Cross-cutting numeric defaults (previously hardcoded in config/eval) ---
DEFAULT_SEED = 42
DEFAULT_BATCH_SIZE = 60
DEFAULT_FP_WEIGHT = 3

# --- Canonical pipeline stage keys (taxonomy.md) ---
STAGE_EXACT = "exact"
STAGE_FUZZY_UTR = "fuzzy_utr"
STAGE_AMOUNT_DATE = "amount_date"
STAGE_BATCH_SUM = "batch_sum"
STAGE_LLM_TIEBREAK = "llm_tiebreak"
ALL_STAGES = (STAGE_EXACT, STAGE_FUZZY_UTR, STAGE_AMOUNT_DATE, STAGE_BATCH_SUM, STAGE_LLM_TIEBREAK)

# --- Canonical exception reason codes (taxonomy.md) ---
REASON_NO_CANDIDATE = "NO_CANDIDATE"
REASON_MULTIPLE_CANDIDATES = "MULTIPLE_CANDIDATES"
REASON_AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
REASON_UTR_UNRESOLVED = "UTR_UNRESOLVED"
REASON_DATE_OUT_OF_WINDOW = "DATE_OUT_OF_WINDOW"
REASON_BATCH_PARTITION_AMBIGUOUS = "BATCH_PARTITION_AMBIGUOUS"

# --- Canonical exception event types (taxonomy.md) ---
EVENT_CREATED = "CREATED"
EVENT_MAKER_PROPOSED = "MAKER_PROPOSED"
EVENT_CHECKER_APPROVED = "CHECKER_APPROVED"
EVENT_CHECKER_REJECTED = "CHECKER_REJECTED"

# --- Scenario categories (internal to the data generator) ---
CATEGORY_EXACT = "exact"
CATEGORY_FUZZY = "fuzzy"
CATEGORY_BATCHED = "batched"
CATEGORY_AMBIGUOUS = "ambiguous"
CATEGORY_ORPHAN = "orphan"
