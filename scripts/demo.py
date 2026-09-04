#!/usr/bin/env python3
"""ReconAgent demo: generate -> reconcile -> score -> print headline numbers.

One-command product demo. Reproduces the *honest* numbers, not a cherry-picked
screenshot: match vs review vs exception rates, the per-stage breakdown, and the
offline scorecard against the hidden answer key (with the 3x false-positive
penalty that is a deliberate design choice).

Run:
    python scripts/demo.py            # seed 42
    python scripts/demo.py --seed 7   # any seed
"""
from __future__ import annotations

import argparse
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
from backend.eval.score import score_reconciliation

import pandas as pd
import json


def _fmt_pct(x: float) -> str:
    return f"{x:.1f}%"


def run(data_dir: Path, seed: int) -> int:
    print("=" * 60)
    print("  ReconAgent — one-command demo")
    print(f"  seed {seed} · synthetic data only (INR paise integers)")
    print("=" * 60)

    # 1. Generate the dataset + hidden answer key.
    cfg = build_config(seed=seed)
    dataset = generate_to_disk(data_dir, cfg)
    n_settlements = len(dataset.scenarios)
    n_lines = len(dataset.lines)
    print(f"\n1) Generated {n_settlements} settlements, {n_lines} bank lines (seed {seed}).")

    # 2. Reconcile.
    settlements = pd.read_csv(data_dir / "settlements.csv").to_dict("records")
    lines = pd.read_csv(data_dir / "bank_statement.csv").to_dict("records")
    result = reconcile(settlements, lines)
    rp = result.report
    matches = [m.as_dict() for m in result.matches]

    print(f"\n2) Reconciled — {rp['matched_settlements']}/{rp['total_settlements']} matched.")
    print(f"   match_rate    {_fmt_pct(rp['match_rate'])}   (engine confidence)")
    print(f"   review_rate   {_fmt_pct(rp['review_rate'])}   (60-84 band -> Maker)")
    print(f"   exception_rate {_fmt_pct(rp['exception_rate'])}   (hard exceptions)")
    print("   per-stage:")
    for stage in ("exact", "fuzzy_utr", "amount_date", "batch_sum", "llm_tiebreak"):
        n = rp.get("by_stage", {}).get(stage, 0)
        if n:
            print(f"      {stage:<13} {n:>3}")

    # 3. Score against the hidden answer key (scoring scope only).
    answer_key = json.loads((data_dir / "answer_key.json").read_text(encoding="utf-8"))
    card = score_reconciliation(answer_key, matches)
    print(f"\n3) Offline accuracy vs hidden answer key (FP penalized {card.penalty_weight}x):")
    print(f"   precision {card.precision:.3f}   recall {card.recall:.3f}   F1 {card.f1:.3f}   "
          f"penalized {card.penalized_score:.3f}")
    print(f"   hits {card.hits} / expected {card.expected_matches} · "
          f"false positives {card.false_positives} · misses {card.misses}")

    print("\n" + "=" * 60)
    print("  Pitch: verification capacity, not generation speed, is the bottleneck.")
    print("=" * 60)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ReconAgent demo (generate -> run -> score)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--data-dir", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.data_dir is None:
        from backend.config import settings
        data_dir = settings.data_dir
    else:
        data_dir = args.data_dir

    return run(data_dir, args.seed)


if __name__ == "__main__":
    sys.exit(main())