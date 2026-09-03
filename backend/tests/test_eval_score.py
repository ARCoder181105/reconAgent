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
