"""data_generator package constants.

Central home for the synthetic-data tunables and literals that were previously
scattered across ``generate_settlements.py`` / ``generate_statement.py`` /
``generator.py``: UTR alphabet, bank names, fee curves, column layouts, and
messiness probabilities.
"""
from __future__ import annotations

# --- Settlement scenario shapes ---
UTR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"
UTR_LENGTH = 16
SETTLEMENT_ID_ALPHABET = "0123456789abcdef"
SETTLEMENT_ID_PREFIX = "setl_"
SETTLEMENT_ID_LEN = 12

BATCH_GROUP_SIZE = 3  # settlements sharing one aggregated bank credit

# --- Fee / tax curves (approximations of an MDR-style model) ---
MDR_FEE_MIN = 0.015       # 1.5% of gross
MDR_FEE_MAX = 0.025       # 2.5% of gross
GST_ON_FEES_RATE = 0.18   # 18% GST on MDR fees
REFUND_PROB = 0.70        # probability a settlement has no refunds
REFUND_PCT_MIN = 0.02
REFUND_PCT_MAX = 0.08
ADJUSTMENT_PROB = 0.15
ADJUSTMENT_PCT_MIN = 0.01  # negative adjustment (abs)
ADJUSTMENT_PCT_MAX = 0.05

# --- Gross-order value bands (rounded paise) ---
GROSS_BANDS_RUPEES = (149, 299, 499, 899, 1299, 2499, 4999, 9999, 14999, 24999)

# --- Bank statement generation ---
BANKS = ("HDFC", "ICICI", "Kotak", "Axis", "SBI")
INITIAL_BALANCE = 100000.0
ORPHAN_CHARGE_PROB = 0.05        # fraction of batch_size as standalone debit charges
OFF_BY_FEE_PROB = 0.20           # chance a fuzzy line is credited net-of-bank-fee
BANK_CHARGE_PAISE = (500, 118, 590, 236, 354, 1770)
ORPHAN_CHARGE_DATE = "2026-08-31"
CHARGE_DESCRIPTIONS = (
    "BANK CHARGES",
    "CHQ RETURN CHARGES",
    "SMS/ALERT CHARGES",
    "DEBIT TO PROCESS FEE",
)

# --- Column layouts for the emitted CSVs ---
SETTLEMENT_COLUMNS = [
    "settlement_id", "utr", "settlement_date", "no_of_transactions",
    "gross_amount", "fees", "tax_gst", "refunds_deducted", "adjustments",
    "net_amount", "status", "bank_account_last4",
]
STATEMENT_COLUMNS = [
    "line_id", "txn_date", "value_date", "description", "ref_no",
    "debit", "credit", "balance", "bank_name",
]
