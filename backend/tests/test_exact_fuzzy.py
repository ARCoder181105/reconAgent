"""Iteration 03: exact + fuzzy UTR match tests."""
from __future__ import annotations

from backend.app.matcher.exact_match import exact_match
from backend.app.matcher.fuzzy_match import fuzzy_match

UTR = "1597813219E1PQ6W"


def _settlement(net_paise: int = 97640, utr: str = UTR) -> dict:
    return {
        "settlement_id": "setl_a",
        "utr": utr,
        "settlement_date": "2026-09-01",
        "net_amount": net_paise,
    }


def _line(desc: str = "", ref: str = "", credit_paise: int = 97640) -> dict:
    return {
        "line_id": "bl_1",
        "txn_date": "2026-09-02",
        "value_date": "2026-09-02",
        "description": desc,
        "ref_no": ref,
        "credit_paise": credit_paise,
        "debit_paise": None,
        "bank_name": "HDFC",
    }


# --- exact ---
def test_exact_verbatim_utr():
    v = exact_match(_settlement(), _line(desc=f"NEFT-{UTR}-RAZORPAY"))
    assert v.matched and v.confidence == 95


def test_exact_utr_in_ref_no():
    v = exact_match(_settlement(), _line(desc="NEFT", ref=UTR))
    assert v.matched


def test_exact_utr_missing():
    v = exact_match(_settlement(), _line(desc="BY TRANSFER-CLG"))
    assert not v.matched


def test_exact_amount_mismatch_rejected():
    v = exact_match(_settlement(), _line(desc=f"NEFT-{UTR}", credit_paise=100000))
    assert not v.matched


# --- fuzzy ---
def test_fuzzy_truncated_utr():
    # Bank shows only first 13 chars.
    v = fuzzy_match(_settlement(), _line(desc=f"NEFT-{UTR[:13]}-RAZORPAY", credit_paise=97640))
    assert v.matched and v.confidence >= 85


def test_fuzzy_midstring_utr():
    v = fuzzy_match(_settlement(), _line(desc=f"CMS001/RZRPY/{UTR}/BATCH", credit_paise=97640))
    assert v.matched


def test_fuzzy_suffix_utr():
    v = fuzzy_match(_settlement(), _line(desc=f"UCR-{UTR[-13:]}-RAZORPAY", credit_paise=97640))
    assert v.matched


def test_fuzzy_wrong_amount_rejected():
    v = fuzzy_match(_settlement(), _line(desc=f"NEFT-{UTR[:13]}", credit_paise=500))
    assert not v.matched


def test_fuzzy_unrelated_token_rejected():
    v = fuzzy_match(_settlement(), _line(desc="NEFT-AAAAAAAAAAAAAAAA", credit_paise=97640))
    assert not v.matched
