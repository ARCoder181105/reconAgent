"""Data generator coordinator.

Runs the whole synthetic pipeline: build settlement scenarios, generate messy
bank lines, assemble the hidden answer key, and write all three artifacts.

The answer key is deliberately kept separate from the matcher path — the matcher
only ever reads the two CSVs.
"""
from __future__ import annotations

import csv
from pathlib import Path

from backend.app.data_generator.answer_key_generator import (
    build_answer_key,
    write_answer_key,
)
from backend.app.data_generator.constants import (
    SETTLEMENT_COLUMNS,
    STATEMENT_COLUMNS,
)
from backend.app.data_generator.generate_settlements import (
    SettlementScenario,
    generate_settlements,
)
from backend.app.data_generator.generate_statement import (
    BankLine,
    generate_statement,
)
from backend.app.data_generator.seed_config import SeedConfig, build_config


def _settlement_row(s: SettlementScenario) -> list:
    return [
        s.settlement_id, s.utr, s.settlement_date, s.no_of_transactions,
        s.gross_amount, s.fees, s.tax_gst, s.refunds_deducted, s.adjustments,
        s.net_amount, s.status, s.bank_account_last4,
    ]


def _statement_row(b: BankLine) -> list:
    return [
        b.line_id, b.txn_date, b.value_date, b.description, b.ref_no,
        "" if b.debit is None else b.debit,
        "" if b.credit is None else b.credit,
        b.balance,
        b.bank_name,
    ]


def write_settlements_csv(scenarios: list[SettlementScenario], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(SETTLEMENT_COLUMNS)
        for s in scenarios:
            writer.writerow(_settlement_row(s))


def write_statement_csv(lines: list[BankLine], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(STATEMENT_COLUMNS)
        for line in lines:
            writer.writerow(_statement_row(line))


class GeneratedData:
    """Container for the generator outputs."""

    def __init__(self, scenarios, lines, answer_key):
        self.scenarios: list[SettlementScenario] = scenarios
        self.lines: list[BankLine] = lines
        self.answer_key: dict = answer_key


def generate(cfg: SeedConfig | None = None) -> GeneratedData:
    """Produce scenarios + bank lines + answer key in memory."""
    cfg = cfg or build_config()
    import random

    rng = random.Random(cfg.seed)
    scenarios = generate_settlements(cfg, rng)
    lines = generate_statement(scenarios, cfg, rng)
    answer_key = build_answer_key(scenarios, lines)
    return GeneratedData(scenarios, lines, answer_key)


def generate_to_disk(
    out_dir: Path | None = None,
    cfg: SeedConfig | None = None,
) -> GeneratedData:
    """Generate and write the two CSVs + answer key to `out_dir`.

    Defaults to `backend/data/`. The CSVs are what the matcher consumes; the
    answer key is only for the scoring script.
    """
    cfg = cfg or build_config()
    from backend.config import settings

    out_dir = out_dir or settings.data_dir
    data = generate(cfg)

    settlements_path = out_dir / "settlements.csv"
    statement_path = out_dir / "bank_statement.csv"
    answer_key_path = out_dir / "answer_key.json"

    write_settlements_csv(data.scenarios, settlements_path)
    write_statement_csv(data.lines, statement_path)
    write_answer_key(data.answer_key, answer_key_path)

    return data
