"""Iteration 03: exact + fuzzy UTR match tests."""
from __future__ import annotations

from backend.app.matcher.exact_match import exact_match
from backend.app.matcher.fuzzy_match import dominant_utr_match, fuzzy_match

UTR = "1597813219E1PQ6W"


def _settlement(net_paise: int = 97640, utr: str = UTR, sid: str = "setl_a") -> dict:
    return {
        "settlement_id": sid,
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


# --- dominant-UTR recovery (It9 fix) ---
def test_dominant_utr_breaks_amount_tie():
    """Two near-identical amounts make amount+date ambiguous; a clearly dominant
    UTR disambiguates to the intended settlement."""
    line = _line(
        ref="L0FBCCSP2B7UV6R1",
        credit_paise=29188,
    )
    # bank UTR L0FBCCSP2B7UV6R1 vs true LXCBFCSP2B7UV6R1: score ~0.81, and a
    # distractor with a near-identical amount (60 paise off) but unrelated UTR.
    dom = dominant_utr_match(
        line,
        [
            _settlement(29188, "LXCBFCSP2B7UV6R1", sid="setl_true"),
            _settlement(29128, "R5HT4RKGDU02RLWW", sid="setl_noise"),
        ],
    )
    assert dom is not None
    sid, verdict = dom
    assert sid == "setl_true"
    assert verdict.matched
    assert verdict.confidence < 85  # review band, never auto-close


def test_dominant_utr_refuses_no_clear_margin():
    """With no UTR dominance (no candidate scores above the floor), returns None."""
    line = _line(ref="BY TRANSFER-CLG", credit_paise=29188)
    dom = dominant_utr_match(
        line,
        [
            _settlement(29188, "LXCBFCSP2B7UV6R1", sid="setl_a"),
            _settlement(29128, "R5HT4RKGDU02RLWW", sid="setl_b"),
        ],
    )
    assert dom is None


def test_dominant_utr_refuses_tight_margin():
    """Two settlements with similar UTR similarity must be left ambiguous."""
    base = "LXCBFCSP2B7UV6R1"
    line = _line(ref="LXCBFCSP2B7UV6R1", credit_paise=29900)
    a = _settlement(29900, base, sid="setl_a")
    b = _settlement(29900, "LXCBFCSP2B7UV6R2", sid="setl_b")  # off by one char
    dom = dominant_utr_match(line, [a, b])
    # Off-by-one rival has a high score too -> ratio below 1.5 -> refuse.
    assert dom is None
