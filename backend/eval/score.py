"""Offline scoring vs the hidden answer key.

This is the ONLY module that may read the answer key. It is deliberately kept
out of the ``matcher`` package so the matching path can never see ground truth.

Confusion model over the settlement population:

- ``hits``        : a settlement that *should* have a bank line and DID get
                    matched to the correct line.
- ``fp``          : false positive — matched a settlement to the WRONG line, OR
                    matched an "orphan"/not-credited settlement that must have
                    NO line, OR bound an orphan bank charge line to a settlement.
- ``misses``      : a settlement that should have been matched but wasn't.

Per the constraints, false positives are penalized 3x:
    penalized_score = max(0, hits - 3*fp) / expected_matches
Additionally precision / recall / f1 are reported for reference.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.eval.constants import DEFAULT_PENALTY_WEIGHT


@dataclass
class ScoreCard:
    """Full scoring breakdown for one batch."""

    expected_matches: int = 0
    hits: int = 0
    false_positives: int = 0
    misses: int = 0
    orphan_lines_total: int = 0
    penalty_weight: int = DEFAULT_PENALTY_WEIGHT
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    penalized_score: float = 0.0
    wrong_lines: list[tuple[str, str, str]] = field(default_factory=list)  # (sid, got, expected)
    # Amount-weighted variants (paise). precision/recall stay denominated on the
    # expected-to-match subset; misrouted_pct is denominated on the whole book.
    hits_amount: int = 0
    fp_amount: int = 0
    fn_amount: int = 0
    total_amount: int = 0
    amount_precision: float = 0.0
    amount_recall: float = 0.0
    misrouted_pct: float = 0.0
    penalized_misrouted_pct: float = 0.0

    def as_dict(self) -> dict:
        return {
            "expected_matches": self.expected_matches,
            "hits": self.hits,
            "false_positives": self.false_positives,
            "misses": self.misses,
            "orphan_lines_total": self.orphan_lines_total,
            "penalty_weight": self.penalty_weight,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "penalized_score": self.penalized_score,
            "wrong_lines": self.wrong_lines,
            "hits_amount": self.hits_amount,
            "fp_amount": self.fp_amount,
            "fn_amount": self.fn_amount,
            "total_amount": self.total_amount,
            "amount_precision": self.amount_precision,
            "amount_recall": self.amount_recall,
            "misrouted_pct": self.misrouted_pct,
            "penalized_misrouted_pct": self.penalized_misrouted_pct,
        }


def _settlement_match_map(matches) -> dict[str, str]:
    """settlement_id -> line_id from the reconciler's matches (1:1)."""
    out: dict[str, str] = {}
    for m in matches:
        out.setdefault(m["settlement_id"], m["line_id"])
    return out


def _amount(settlement_info: dict) -> int:
    """net_amount in paise (0 if absent so weighting stays well-defined)."""
    return int(settlement_info.get("net_amount") or 0)


def score_reconciliation(answer_key: dict, matches) -> ScoreCard:
    """Score reconcile ``matches`` against the hidden ``answer_key``.

    ``matches`` is an iterable of dicts with keys ``settlement_id`` and
    ``line_id`` (e.g. ``ResolvedMatch.as_dict()``).
    """
    settlements_truth = answer_key["settlements"]  # sid -> {line_id|None, category}
    orphan_bank_lines = set(answer_key.get("orphan_lines", []))
    matched = _settlement_match_map(matches)

    card = ScoreCard()
    card.orphan_lines_total = len(orphan_bank_lines)

    # Settlements that must be matched (have a real bank line in truth).
    expected_sids = [sid for sid, info in settlements_truth.items() if info["line_id"]]

    # Whole book (all settlements) is the denominator for misrouted_pct.
    card.total_amount = sum(_amount(info) for info in settlements_truth.values())

    # fp on *expected* settlements (wrong-line matches) — the precision base.
    fp_expected_amount = 0

    for sid, info in settlements_truth.items():
        truth_line = info["line_id"]
        got_line = matched.get(sid)
        amount = _amount(info)

        if truth_line is not None:
            card.expected_matches += 1
            if got_line == truth_line:
                card.hits += 1
                card.hits_amount += amount
            else:
                if got_line is not None:
                    card.false_positives += 1  # matched to the wrong line
                    card.fp_amount += amount
                    fp_expected_amount += amount
                    card.wrong_lines.append((sid, got_line, truth_line))
                card.misses += 1
                card.fn_amount += amount
        else:
            # Orphan/not-credited settlement must stay unmatched.
            if got_line is not None:
                card.false_positives += 1
                card.fp_amount += amount
                card.wrong_lines.append((sid, got_line, "<none>"))

    # A match that binds an orphan bank charge line is a false positive too.
    # Weight it by the settlement it was wrongly bound to (bank lines carry no
    # settlement-level amount of their own). Excluded from the precision base.
    for m in matches:
        if m["line_id"] in orphan_bank_lines:
            card.false_positives += 1
            bound_amount = _amount(settlements_truth.get(m["settlement_id"], {}))
            card.fp_amount += bound_amount
            card.wrong_lines.append((m["settlement_id"], m["line_id"], "<orphan-line>"))

    tp = card.hits
    fp = card.false_positives
    fn = card.misses
    if tp + fp > 0:
        card.precision = round(tp / (tp + fp), 4)
    if tp + fn > 0:
        card.recall = round(tp / (tp + fn), 4)
    if card.precision + card.recall > 0:
        card.f1 = round(2 * card.precision * card.recall / (card.precision + card.recall), 4)

    if card.expected_matches:
        card.penalized_score = round(max(0.0, (tp - card.penalty_weight * fp) / card.expected_matches), 4)
    else:
        card.penalized_score = 1.0 if fp == 0 else 0.0

    # --- amount-weighted accuracy (paise) ---
    # precision/recall are denominated on expected-to-match settlements only
    # (orphan FPs are excluded from the precision base — correct classification
    # base). misrouted_pct is denominated on the whole book.
    tp_a, fn_a = card.hits_amount, card.fn_amount
    if tp_a + fp_expected_amount > 0:
        card.amount_precision = round(tp_a / (tp_a + fp_expected_amount), 4)
    if tp_a + fn_a > 0:
        card.amount_recall = round(tp_a / (tp_a + fn_a), 4)
    if card.total_amount > 0:
        card.misrouted_pct = round(100.0 * (card.fp_amount + fn_a) / card.total_amount, 4)
        # Same 3x false-positive weight as the row-count penalized_score, so the
        # money metric and the count metric carry consistent risk weighting.
        card.penalized_misrouted_pct = round(
            100.0 * (card.penalty_weight * card.fp_amount + fn_a) / card.total_amount, 4
        )

    return card
