"""Iteration 03: normalizer tests."""
from __future__ import annotations

from backend.app.matcher.normalizer import (
    normalize_bank_line,
    normalize_settlement,
    parse_date,
    rupees_to_paise,
)


def test_parse_date_mixed_formats():
    from datetime import date

    assert parse_date("05-09-2026") == date(2026, 9, 5)
    assert parse_date("05/09/26") == date(2026, 9, 5)
    assert parse_date("2026-09-05") == date(2026, 9, 5)
    assert parse_date("05/09/2026") == date(2026, 9, 5)
    assert parse_date("") is None


def test_rupees_to_paise():
    assert rupees_to_paise(1234.56) == 123456
    assert rupees_to_paise("1,234.56") == 123456
    assert rupees_to_paise("₹1,234.56") == 123456
    assert rupees_to_paise(None) is None
    assert rupees_to_paise("") is None


def test_normalize_settlement():
    rec = normalize_settlement(
        {
            "settlement_id": "setl_abc",
            "utr": " 1597813219E1PQ6W ",
            "settlement_date": "2026-09-01",
            "net_amount": "97640",
            "gross_amount": "100000",
            "fees": "2000",
            "tax_gst": "360",
            "refunds_deducted": "0",
            "adjustments": "-400",
            "status": "processed",
            "bank_account_last4": "1234",
        }
    )
    assert rec["utr"] == "1597813219E1PQ6W"
    assert rec["net_amount"] == 97640
    assert rec["settlement_date"] == "2026-09-01"


def test_normalize_bank_line_mixed_dates():
    rec = normalize_bank_line(
        {
            "line_id": "bl_1",
            "txn_date": "05-09-2026",
            "value_date": "",
            "description": "  NEFT-XYZ  ",
            "ref_no": "",
            "credit": "1,234.56",
            "debit": "",
            "balance": 98765.43,
            "bank_name": "hdfc",
        }
    )
    assert rec["txn_date"] == "2026-09-05"
    assert rec["credit_paise"] == 123456
    assert rec["description"] == "NEFT-XYZ"
    assert rec["bank_name"] == "HDFC"
