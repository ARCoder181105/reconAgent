"""Stage 0 — Normalize.

Turns raw CSV records into canonical form so no downstream stage compares raw
strings/amounts:

- currency symbols + thousands separators stripped
- every date parsed to ISO YYYY-MM-DD
- text uppercased + trimmed
- amounts converted to integer paise (bank rupees float -> paise int)
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime

# Matches currency-symbol-prefixed numbers with optional thousands separators.
_NUM_STRIP = re.compile(r"[^\d.,-]")
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%d/%m/%y",
    "%d.%m.%Y",
    "%Y/%m/%d",
)


def parse_date(value: str | None) -> date | None:
    """Parse a date string in any supported format to a datetime.date."""
    if not value:
        return None
    s = str(value).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def rupees_to_paise(value) -> int | None:
    """Convert a bank-statement money value (float rupees) to integer paise.

    Handles strings like "1,234.56", "₹1,234.56", or already-numeric floats.
    Returns None for blank/None input.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        num = float(value)
    else:
        cleaned = _NUM_STRIP.sub("", str(value))
        cleaned = cleaned.replace(",", "")  # remove thousands separators
        try:
            num = float(cleaned)
        except ValueError:
            return None
    return int(round(num * 100))


def normalize_text(value: str | None) -> str:
    """Uppercase + strip whitespace. Returns '' for None."""
    if not value:
        return ""
    return str(value).strip().upper()


def normalize_settlement(rec: dict) -> dict:
    """Canonicalize a settlements.csv row (or ORM-dict)."""
    return {
        "settlement_id": str(rec["settlement_id"]),
        "utr": normalize_text(rec.get("utr")),
        "settlement_date": (parse_date(rec.get("settlement_date")) or date.min).isoformat(),
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
    credit_paise = rupees_to_paise(rec.get("credit"))
    debit_paise = rupees_to_paise(rec.get("debit"))
    return {
        "line_id": str(rec["line_id"]),
        "txn_date": (parse_date(rec.get("txn_date")) or date.min).isoformat(),
        "value_date": (parse_date(rec.get("value_date")) or date.min).isoformat(),
        "description": normalize_text(rec.get("description")),
        "ref_no": normalize_text(rec.get("ref_no")),
        "credit_paise": credit_paise,
        "debit_paise": debit_paise,
        "bank_name": normalize_text(rec.get("bank_name")),
    }
