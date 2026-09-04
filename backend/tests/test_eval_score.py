"""Iteration 06: offline scoring vs hidden answer key tests."""
from __future__ import annotations

from backend.eval.score import score_reconciliation


def _answer_key(settlements: dict, orphan_lines: list[str] | None = None) -> dict:
    return {
        "settlements": settlements,
        "orphan_lines": orphan_lines or [],
    }


def test_perfect_reconciliation_scores_perfect():
    ak = _answer_key(
        {
            "setl_a": {"line_id": "bl_1", "category": "exact"},
            "setl_b": {"line_id": "bl_2", "category": "fuzzy"},
        }
    )
    matches = [
        {"settlement_id": "setl_a", "line_id": "bl_1"},
        {"settlement_id": "setl_b", "line_id": "bl_2"},
    ]
    card = score_reconciliation(ak, matches)
    assert card.hits == 2
    assert card.false_positives == 0
    assert card.misses == 0
    assert card.penalized_score == 1.0
    assert card.precision == 1.0 and card.recall == 1.0 and card.f1 == 1.0


def test_missed_match_counts_as_false_negative():
    ak = _answer_key({"setl_a": {"line_id": "bl_1", "category": "exact"}})
    card = score_reconciliation(ak, [])
    assert card.misses == 1
    assert card.hits == 0
    assert card.recall == 0.0


def test_wrong_line_is_false_positive_penalized_3x():
    ak = _answer_key({"setl_a": {"line_id": "bl_1", "category": "exact"}})
    matches = [{"settlement_id": "setl_a", "line_id": "bl_WRONG"}]
    card = score_reconciliation(ak, matches)
    # Matched to the wrong line: +1 miss, +1 fp.
    assert card.misses == 1
    assert card.false_positives == 1
    assert card.penalized_score == 0.0  # (0 - 3*1)/1 clamped to 0


def test_orphan_settlement_matched_is_false_positive():
    ak = _answer_key({"setl_o": {"line_id": None, "category": "orphan"}})
    matches = [{"settlement_id": "setl_o", "line_id": "bl_9"}]
    card = score_reconciliation(ak, matches)
    assert card.false_positives == 1
    assert card.penalized_score == 0.0


def test_orphan_bank_line_bound_is_false_positive():
    ak = _answer_key(
        {"setl_a": {"line_id": "bl_1", "category": "exact"}},
        orphan_lines=["bl_X"],
    )
    matches = [
        {"settlement_id": "setl_a", "line_id": "bl_1"},
        {"settlement_id": "setl_a", "line_id": "bl_X"},
    ]
    card = score_reconciliation(ak, matches)
    assert card.false_positives == 1  # the bl_X binding


def test_penalty_weight_makes_fp_cost_three_hits():
    ak = _answer_key(
        {
            "setl_a": {"line_id": "bl_1", "category": "exact"},
            "setl_b": {"line_id": "bl_2", "category": "exact"},
            "setl_c": {"line_id": "bl_3", "category": "exact"},
            "setl_d": {"line_id": "bl_4", "category": "exact"},
        }
    )
    # 3 correct hits + 1 fp -> (3 - 3*1)/4 = 0
    matches = [
        {"settlement_id": "setl_a", "line_id": "bl_1"},
        {"settlement_id": "setl_b", "line_id": "bl_2"},
        {"settlement_id": "setl_c", "line_id": "bl_3"},
        {"settlement_id": "setl_d", "line_id": "bl_WRONG"},
    ]
    card = score_reconciliation(ak, matches)
    assert card.hits == 3
    assert card.false_positives == 1
    assert card.penalized_score == 0.0


# --- amount-weighted accuracy -------------------------------------------------- #
#
# Concrete paise scenario (expected-only precision/recall, whole-book misrouted):
#   setl_a  ₹100 (expected, clicked)   -> hit
#   setl_b  ₹200 (expected, wrong)     -> fp+fn
#   setl_c  ₹700 (orphan, matched)     -> fp
# total book = 1000; fp_amt = 900; fn_amt = 200; hits_amt = 100.


def test_amount_weighted_precision_recall_on_expected_only():
    ak = _answer_key(
        {
            "setl_a": {"line_id": "bl_1", "category": "exact", "net_amount": 10000},
            "setl_b": {"line_id": "bl_2", "category": "exact", "net_amount": 20000},
            "setl_c": {"line_id": None, "category": "orphan", "net_amount": 70000},
        }
    )
    matches = [
        {"settlement_id": "setl_a", "line_id": "bl_1"},
        {"settlement_id": "setl_b", "line_id": "bl_WRONG"},
        {"settlement_id": "setl_c", "line_id": "bl_9"},
    ]
    card = score_reconciliation(ak, matches)

    assert card.hits_amount == 10000
    assert card.fp_amount == 90000  # 200 (wrong line) + 700 (orphan matched)
    assert card.fn_amount == 20000
    assert card.total_amount == 100000

    # precision/recall are denominated on expected-to-match settlements (a+b):
    assert card.amount_precision == round(10000 / (10000 + 20000), 4)  # 1/3
    assert card.amount_recall == round(10000 / (10000 + 20000), 4)    # 1/3

    # misrouted is denominated on the whole book (a+b+c): (900 + 200)/1000 = 1.1
    assert card.misrouted_pct == 110.0


def test_penalized_misrouted_pct_applies_3x_to_false_positives():
    ak = _answer_key(
        {
            "setl_a": {"line_id": "bl_1", "category": "exact", "net_amount": 10000},
            "setl_c": {"line_id": None, "category": "orphan", "net_amount": 70000},
        }
    )
    matches = [
        {"settlement_id": "setl_a", "line_id": "bl_1"},   # hit
        {"settlement_id": "setl_c", "line_id": "bl_9"},   # fp
    ]
    card = score_reconciliation(ak, matches)

    assert card.fp_amount == 70000
    assert card.fn_amount == 0
    assert card.misrouted_pct == round(100.0 * 70000 / 80000, 4)          # 87.5 raw
    # penalized weights the fp 3x: (3*70000 + 0)/80000 = 2.625
    assert card.penalized_misrouted_pct == round(100.0 * 3 * 70000 / 80000, 4)
