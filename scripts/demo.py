#!/usr/bin/env python3
"""ReconAgent demo: generate -> reconcile -> score -> print headline numbers.

One-command product demo. Reproduces the *honest* numbers, not a cherry-picked
screenshot: match vs review vs exception rates, the per-stage breakdown, the
offline scorecard against the hidden answer key (row-count + amount-weighted,
with the 3x false-positive penalty that is a deliberate design choice), and a
multi-seed robustness pass (mean/stdev over seeds 1..N).

Run:
    python scripts/demo.py              # seed 42
    python scripts/demo.py --seed 7     # any seed
    python scripts/demo.py --multi 10   # robustness over seeds 1..10
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

# Ensure the repo root is importable when run as `python scripts/demo.py`.
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.app.data_generator.generator import generate_to_disk
from backend.app.data_generator.seed_config import build_config
from backend.app.matcher.reconcile import reconcile
from backend.constants import DEFAULT_SEED
from backend.eval.score import ScoreCard, score_reconciliation

import pandas as pd


def _fmt_pct(x: float) -> str:
    return f"{x:.2f}%"


_METRICS = (
    "precision",
    "recall",
    "f1",
    "penalized_score",
    "amount_precision",
    "amount_recall",
    "misrouted_pct",
    "penalized_misrouted_pct",
)


def _score_seed(data_dir: Path, seed: int) -> tuple[dict, ScoreCard]:
    """Generate + reconcile + score one seed; return (report_dict, scorecard)."""
    cfg = build_config(seed=seed)
    dataset = generate_to_disk(data_dir, cfg)
    settlements = pd.read_csv(data_dir / "settlements.csv").to_dict("records")
    lines = pd.read_csv(data_dir / "bank_statement.csv").to_dict("records")
    result = reconcile(settlements, lines)
    matches = [m.as_dict() for m in result.matches]
    answer_key = json.loads((data_dir / "answer_key.json").read_text(encoding="utf-8"))
    card = score_reconciliation(answer_key, matches)
    return result.report, card


def run(data_dir: Path, seed: int) -> int:
    print("=" * 60)
    print("  ReconAgent — one-command demo")
    print(f"  seed {seed} · synthetic data only (INR paise integers)")
    print("=" * 60)

    rp, card = _score_seed(data_dir, seed)
    n_settlements = rp["total_settlements"]
    n_lines = rp["total_bank_lines"]
    print(f"\n1) Generated {n_settlements} settlements, {n_lines} bank lines (seed {seed}).")

    print(f"\n2) Reconciled — {rp['matched_settlements']}/{n_settlements} matched.")
    print(f"   match_rate    {_fmt_pct(rp['match_rate'])}   (engine confidence)")
    print(f"   review_rate   {_fmt_pct(rp['review_rate'])}   (60-84 band -> Maker)")
    print(f"   exception_rate {_fmt_pct(rp['exception_rate'])}   (hard exceptions)")
    print("   per-stage:")
    for stage in ("exact", "fuzzy_utr", "amount_date", "batch_sum", "llm_tiebreak"):
        n = rp.get("by_stage", {}).get(stage, 0)
        if n:
            print(f"      {stage:<13} {n:>3}")

    print(f"\n3) Offline accuracy vs hidden answer key (FP penalized {card.penalty_weight}x):")
    print(f"   row:   precision {card.precision:.3f}  recall {card.recall:.3f}  "
          f"F1 {card.f1:.3f}  penalized {card.penalized_score:.3f}")
    print(f"          hits {card.hits}/{card.expected_matches} · fp {card.false_positives} · "
          f"misses {card.misses}")
    print(f"   ₹:     precision {card.amount_precision:.3f}  recall {card.amount_recall:.3f}  "
          f"misrouted {_fmt_pct(card.misrouted_pct)}  penalized {_fmt_pct(card.penalized_misrouted_pct)}")
    print(f"          of ₹{card.total_amount / 100:,.0f} total · fp ₹{card.fp_amount / 100:,.0f} · "
          f"misses ₹{card.fn_amount / 100:,.0f}")

    print("\n" + "=" * 60)
    print("  Pitch: verification capacity, not generation speed, is the bottleneck.")
    print("=" * 60)
    return 0


def run_multi(data_dir: Path, n: int) -> int:
    print("=" * 60)
    print("  ReconAgent — multi-seed robustness (mean/stdev over N random runs)")
    print(f"  seeds 1..{n} · a distribution, not a single cherry-picked run")
    print("=" * 60)

    rows: list[dict] = []
    for seed in range(1, n + 1):
        rp, card = _score_seed(data_dir, seed)
        row = {m: getattr(card, m) for m in _METRICS}
        rows.append({"seed": seed, **row})
        match = rp["matched_settlements"]
        print(f"   seed {seed:<3} matched {match:>2}/{rp['total_settlements']:<2} "
              f"match_rate {rp['match_rate']:5.1f}%  precision {card.precision:.3f}  "
              f"recall {card.recall:.3f}  F1 {card.f1:.3f}  ₹misrouted {_fmt_pct(card.misrouted_pct)}")

    print("\n   Summary (mean over seeds):")
    print(f"   {'metric':<26}{'mean':>10}{'stdev':>10}")
    for m in _METRICS:
        vals = [r[m] for r in rows]
        mean = statistics.mean(vals)
        stdev = statistics.stdev(vals) if len(vals) > 1 else 0.0
        unit = "%" if m in ("misrouted_pct", "penalized_misrouted_pct") else "  "
        print(f"   {m:<26}{mean:>9.3f}{stdev:>10.3f}{unit}")

    print("\n" + "=" * 60)
    print("  Pitch: verification capacity, not generation speed, is the bottleneck.")
    print("=" * 60)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ReconAgent demo (generate -> run -> score)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--multi", type=int, default=0,
                        help="run seeds 1..N and print mean/stdev robustness (overrides --seed)")
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.data_dir is None:
        from backend.config import settings
        data_dir = settings.data_dir
    else:
        data_dir = args.data_dir

    if args.multi:
        return run_multi(data_dir, args.multi)
    return run(data_dir, args.seed)


if __name__ == "__main__":
    sys.exit(main())