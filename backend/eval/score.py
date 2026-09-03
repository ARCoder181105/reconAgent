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
        }


def _settlement_match_map(matches) -> dict[str, str]:
    """settlement_id -> line_id from the reconciler's matches (1:1)."""
    out: dict[str, str] = {}
    for m in matches:
        out.setdefault(m["settlement_id"], m["line_id"])
    return out


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

    for sid, info in settlements_truth.items():
        truth_line = info["line_id"]
        got_line = matched.get(sid)

        if truth_line is not None:
            card.expected_matches += 1
            if got_line == truth_line:
                card.hits += 1
            else:
                if got_line is not None:
                    card.false_positives += 1  # matched to the wrong line
                    card.wrong_lines.append((sid, got_line, truth_line))
                card.misses += 1
        else:
            # Orphan/not-credited settlement must stay unmatched.
            if got_line is not None:
                card.false_positives += 1
                card.wrong_lines.append((sid, got_line, "<none>"))

    # A match that binds an orphan bank charge line is a false positive too.
    for m in matches:
        if m["line_id"] in orphan_bank_lines:
            card.false_positives += 1
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

    return card
