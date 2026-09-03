"""Stage 0 — Normalize.

Turns raw CSV records into canonical form so no downstream stage compares raw
strings/amounts:

- currency symbols + thousands separators stripped
- every date parsed to ISO YYYY-MM-DD
- text uppercased + trimmed
- amounts converted to integer paise (bank rupees float -> paise int)

The low-level conversions live in ``backend/utils`` and are reused elsewhere.
"""
from __future__ import annotations

from datetime import date

from backend.utils.dates import iso_or_min
from backend.utils.money import rupees_to_paise
from backend.utils.text import normalize_text


def normalize_settlement(rec: dict) -> dict:
    """Canonicalize a settlements.csv row (or ORM-dict)."""
    return {
        "settlement_id": str(rec["settlement_id"]),
        "utr": normalize_text(rec.get("utr")),
        "settlement_date": iso_or_min(rec.get("settlement_date")),
        "net_amount": int(rec.get("net_amount") or 0),
        "gross_amount": int(rec.get("gross_amount") or 0),
        "fees": int(rec.get("fees") or 0),
        "tax_gst": int(rec.get("tax_gst") or 0),
        "refunds_deducted": int(rec.get("refunds_deducted") or 0),
        "adjustments": int(rec.get("adjustments") or 0),
        "status": normalize_text(rec.get("status")),
        "bank_account_last4": normalize_text(rec.get("bank_account_last4")),
    }


def normalize_bank_line(rec: dict) -> dict:
    """Canonicalize a bank_statement.csv row (or ORM-dict)."""
    return {
        "line_id": str(rec["line_id"]),
        "txn_date": iso_or_min(rec.get("txn_date")),
        "value_date": iso_or_min(rec.get("value_date")),
        "description": normalize_text(rec.get("description")),
        "ref_no": normalize_text(rec.get("ref_no")),
        "credit_paise": rupees_to_paise(rec.get("credit")),
        "debit_paise": rupees_to_paise(rec.get("debit")),
        "bank_name": normalize_text(rec.get("bank_name")),
    }
