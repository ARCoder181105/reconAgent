"""Offline eval CLI: generate -> reconcile -> score against the answer key.

The hidden answer key is loaded ONLY here (and in the unit tests of the scorer).
Run with:

    python -m backend.eval.run_score [--data-dir PATH] [--seed N]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

from backend.app.data_generator.generator import generate_to_disk
from backend.app.data_generator.seed_config import build_config
from backend.app.matcher.reconcile import reconcile
from backend.eval.score import score_reconciliation
from backend.constants import DEFAULT_SEED


def run(data_dir: Path, seed: int, print_json: bool = True) -> dict:
    cfg = build_config(seed=seed)
    dataset = generate_to_disk(data_dir, cfg)

    settlements = pd.read_csv(data_dir / "settlements.csv").to_dict("records")
    lines = pd.read_csv(data_dir / "bank_statement.csv").to_dict("records")

    result = reconcile(settlements, lines)
    matches = [m.as_dict() for m in result.matches]

    answer_key = json.loads((data_dir / "answer_key.json").read_text(encoding="utf-8"))
    card = score_reconciliation(answer_key, matches)

    output = {
        "seed": seed,
        "report": result.report,
        "scorecard": card.as_dict(),
    }
    if print_json:
        print(json.dumps(output, indent=2, default=str))
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline reconcile + score")
    parser.add_argument("--data-dir", type=Path, default=None, help="output dir (default: settings.data_dir)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args(argv)

    if args.data_dir is None:
        from backend.config import settings

        data_dir = settings.data_dir
    else:
        data_dir = args.data_dir

    run(data_dir, args.seed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
