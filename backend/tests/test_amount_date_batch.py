"""Iteration 04: amount+date and batch-sum match tests."""
from __future__ import annotations

from backend.app.matcher.amount_date_match import amount_date_match
from backend.app.matcher.batch_match import batch_match


def _line(credit_paise: int, txn_date: str = "2026-09-02") -> dict:
    return {
        "line_id": "bl_1",
        "txn_date": txn_date,
        "value_date": txn_date,
        "description": "BY TRANSFER-CLG",
        "ref_no": "",
        "credit_paise": credit_paise,
        "debit_paise": None,
        "bank_name": "HDFC",
    }


def _settlement(sid: str, net_paise: int, date_str: str = "2026-09-01") -> dict:
    return {
        "settlement_id": sid,
        "utr": "",
        "settlement_date": date_str,
        "net_amount": net_paise,
    }


# --- amount + date ---
def test_amount_date_single_candidate():
    res = amount_date_match(
        _line(credit_paise=97640),
        [_settlement("setl_a", 97640)],
    )
    assert res.status == "match"
    assert res.settlement_id == "setl_a"
    assert res.confidence >= 60


def test_amount_date_multiple_candidates_ambiguous():
    res = amount_date_match(
        _line(credit_paise=1234567),
        [
            _settlement("setl_a", 1234567),
            _settlement("setl_b", 1234567),
        ],
    )
    assert res.status == "ambiguous"
    assert len(res.candidates) == 2


def test_amount_date_no_candidate():
    res = amount_date_match(
        _line(credit_paise=97640),
        [_settlement("setl_a", 9999999)],
    )
    assert res.status == "no_candidate"


def test_amount_date_out_of_window():
    # Settlement 10 days earlier then 2-business-day window.
    res = amount_date_match(
        _line(credit_paise=97640, txn_date="2026-09-15"),
        [_settlement("setl_a", 97640, date_str="2026-09-01")],
    )
    assert res.status == "no_candidate"


# --- batch-sum ---
def test_batch_single_partition():
    res = batch_match(
        _line(credit_paise=3000),
        [
            _settlement("setl_a", 1000),
            _settlement("setl_b", 2000),
            _settlement("setl_c", 999999),
        ],
    )
    assert res.status == "match"
    assert sorted(res.settlement_ids) == ["setl_a", "setl_b"]


def test_batch_ambiguous_partitions():
    # Two distinct subsets sum to 3000: (a,b) and (c). Both same-window.
    res = batch_match(
        _line(credit_paise=3000),
        [
            _settlement("setl_a", 1000),
            _settlement("setl_b", 2000),
            _settlement("setl_c", 3000),
        ],
    )
    assert res.status == "ambiguous"


def test_batch_no_partition():
    res = batch_match(
        _line(credit_paise=3000),
        [_settlement("setl_a", 1234), _settlement("setl_b", 5678)],
    )
    assert res.status == "no_partition"


# --- batch date window (It9 fix: wider than amount+date) ---
def test_batch_spans_longer_than_amount_date_window():
    """A batch aggregates settlements trailing several business days behind the
    receipt date; the batch stage must recover them even when amount+date's
    tighter window would exclude them."""
    # bank line on Mon; settlements 1 and 3 business days earlier — outside the
    # ±2 amount+date window but inside the wider batch window.
    line = _line(credit_paise=3000, txn_date="2026-09-04")  # Fri
    # 2026-09-01 Tue, 2026-09-02 Wed -> 3 and 2 business days before Fri
    settlements = [
        _settlement("setl_a", 1000, date_str="2026-09-01"),
        _settlement("setl_b", 2000, date_str="2026-09-02"),
    ]
    res = batch_match(line, settlements)
    assert res.status == "match"
    assert sorted(res.settlement_ids) == ["setl_a", "setl_b"]
