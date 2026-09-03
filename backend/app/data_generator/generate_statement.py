"""Messy bank statement generation.

Consumes settlement scenarios and produces bank lines with deliberate messiness:
truncated/mid-string UTRs, batched aggregate credits, off-by-fee amounts,
mixed date formats, empty descriptions/refs, and standalone orphan lines
(bank charges) that match no settlement.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from backend.constants import (
    CATEGORY_AMBIGUOUS,
    CATEGORY_BATCHED,
    CATEGORY_FUZZY,
    CATEGORY_ORPHAN,
)
from backend.app.data_generator.constants import (
    BANKS,
    BANK_CHARGE_PAISE,
    CHARGE_DESCRIPTIONS,
    INITIAL_BALANCE,
    OFF_BY_FEE_PROB,
    ORPHAN_CHARGE_DATE,
    ORPHAN_CHARGE_PROB,
)
from backend.app.data_generator.generate_settlements import SettlementScenario
from backend.app.data_generator.seed_config import SeedConfig
from backend.utils.money import paise_to_rupees


@dataclass
class BankLine:
    """A generated bank statement line with a stable id and its ground truth."""

    line_id: str
    txn_date: str
    value_date: str
    description: str
    ref_no: str
    debit: float | None
    credit: float | None
    balance: float | None
    bank_name: str
    # Ground-truth markers (answer-key material), not written to CSV:
    settlement_id: str | None = None        # settlement this line correctly matches
    batch_settlement_ids: list[str] = field(default_factory=list)  # for batched credits


def _line_id(idx: int) -> str:
    return f"bl_{idx:05d}"


def _fmt_date(rng: random.Random, iso_date: str) -> str:
    from datetime import date, datetime

    from backend.utils.dates import DATE_FORMATS

    d = date.fromisoformat(iso_date)
    fmt = rng.choice(DATE_FORMATS)
    return datetime(d.year, d.month, d.day).strftime(fmt)


def _money(paise: int) -> float:
    return paise_to_rupees(paise)


def _exact_description(utr: str) -> str:
    return f"NEFT-{utr}-RAZORPAY SOFTWARE PVT LTD"


def _fuzzy_description(rng: random.Random, utr: str) -> tuple[str, str]:
    """Return a (description, ref_no) with a noisy/truncated UTR.

    Varies between: truncated UTR (keep first N), mid-string UTR with prefix/suffix.
    """
    mode = rng.choice(["truncated", "midstring", "suffix"])
    if mode == "truncated":
        n = rng.randint(10, 14)
        return f"NEFT-{utr[:n]}-RAZORPAY", utr[:n]
    if mode == "suffix":
        n = rng.randint(10, 14)
        return f"UCR-{utr[-n:]}-RAZORPAY", utr[-n:]
    # midstring: UTR at a variable offset
    return f"CMS001/RZRPY/{utr}/BATCH", utr


def _ambiguous_description(utr: str) -> tuple[str, str]:
    """High edit-distance UTR: swap/drop a few chars to make matching hard."""
    chars = list(utr)
    if len(chars) >= 6:
        chars[2], chars[4] = chars[4], chars[2]
        chars[1] = "0" if chars[1] != "0" else "1"
    mangled = "".join(chars)
    return f"NEFT-{mangled}-RAZORPAY", mangled


def generate_statement(
    schemes: list[SettlementScenario],
    cfg: SeedConfig,
    rng: random.Random | None = None,
) -> list[BankLine]:
    """Build messy bank lines from settlement scenarios.

    For batch groups across multiple settlement records, produce ONE aggregate
    credit line (many-to-one), regardless of how many scenarios share that group.
    """
    rng = rng or random.Random(cfg.seed + 1)
    lines: list[BankLine] = []
    balance = INITIAL_BALANCE
    idx = 1

    # Pre-compute batched credits per group so we emit one aggregate line per group.
    by_group: dict[str, list[SettlementScenario]] = {}
    for s in schemes:
        if s.category == CATEGORY_BATCHED and s.batch_group:
            by_group.setdefault(tuple(s.batch_group), []).append(s)

    handled_group_lines: set[str] = set()

    def next_line(scenario: SettlementScenario | None, credit_paise, batch_ids, desc, ref, value_date=None):
        nonlocal idx, balance
        credit = _money(credit_paise)
        balance += credit if credit is not None else 0.0
        line = BankLine(
            line_id=_line_id(idx),
            txn_date=scenario.settlement_date if scenario else value_date,
            value_date=value_date or "",
            description=desc,
            ref_no=ref,
            debit=None,
            credit=credit,
            balance=round(balance, 2),
            bank_name=rng.choice(BANKS),
            settlement_id=scenario.settlement_id if scenario else None,
            batch_settlement_ids=list(batch_ids) if batch_ids else [],
        )
        idx += 1
        lines.append(line)
        return line

    for s in schemes:
        if s.category == CATEGORY_BATCHED:
            # Emit the aggregate line only once per group.
            key = tuple(s.batch_group)
            if key in handled_group_lines:
                continue
            handled_group_lines.add(key)
            group_schemes = by_group[key]
            total = sum(m.net_amount for m in group_schemes)
            ids = [m.settlement_id for m in group_schemes]
            next_line(s, total, ids, "BY TRANSFER-CLG", "")
        elif s.category == CATEGORY_ORPHAN:
            # Not-credited: this settlement has NO bank line (a false-negative case).
            continue
        elif s.category == CATEGORY_AMBIGUOUS:
            desc, ref = _ambiguous_description(s.utr)
            next_line(s, s.net_amount, [], desc, ref)
        elif s.category == CATEGORY_FUZZY:
            desc, ref = _fuzzy_description(rng, s.utr)
            # Occasionally simulate an off-by-fee amount (bank-side wire fee).
            credit = s.net_amount - (cfg.off_by_fee_paise if rng.random() < OFF_BY_FEE_PROB else 0)
            next_line(s, credit, [], desc, ref)
        else:  # exact
            desc = _exact_description(s.utr)
            next_line(s, s.net_amount, [], desc, s.utr)

    # Add standalone orphan bank-charge lines (true exceptions, no settlement).
    n_orphan_charges = max(1, int(cfg.batch_size * ORPHAN_CHARGE_PROB))
    for _ in range(n_orphan_charges):
        charge_paise = rng.choice(BANK_CHARGE_PAISE) * 1
        charge = _money(charge_paise)
        balance -= charge
        lines.append(
            BankLine(
                line_id=_line_id(idx),
                txn_date=_fmt_date(rng, ORPHAN_CHARGE_DATE),
                value_date="",
                description=rng.choice(CHARGE_DESCRIPTIONS),
                ref_no="",
                debit=charge,
                credit=None,
                balance=round(balance, 2),
                bank_name=rng.choice(BANKS),
                settlement_id=None,
                batch_settlement_ids=[],
            )
        )
        idx += 1

    return lines
