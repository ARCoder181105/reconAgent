"""Settlement record generation.

Produces deterministic gateway-side settlement records. Each record carries a
`category` and scenario metadata used by the coordinator to drive bank-line
generation and the hidden answer key; these are NOT emitted in the final CSV.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from backend.app.data_generator.seed_config import SeedConfig

# UTRs look like a ~16 char alphanumeric run (e.g. "1597813219E1PQ6W").
_UTR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789"


@dataclass
class SettlementScenario:
    """A planned settlement with the scenario metadata needed downstream."""

    settlement_id: str
    utr: str
    settlement_date: str            # ISO YYYY-MM-DD
    no_of_transactions: int
    gross_amount: int               # paise
    fees: int                       # paise (MDR)
    tax_gst: int                    # paise (18% GST on fees)
    refunds_deducted: int           # paise, may be 0
    adjustments: int                # paise, may be negative
    net_amount: int                 # paise
    status: str
    bank_account_last4: str
    category: str                   # exact | fuzzy | batched | ambiguous | orphan
    # For batched scenarios: the group (list of settlement_ids) that share one bank line.
    batch_group: list[str] = field(default_factory=list)
    # Every settlement (except deliberate orphans) is a true match by default.
    # Orphan settlements still get a settlement record but NO bank line; the
    # "orphan" bank lines are added in the statement generator independently.
    intended_match: bool = True


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


def _make_utr(rng: random.Random) -> str:
    # 16 chars, first char often numeric
    return "".join(rng.choice(_UTR_ALPHABET) for _ in range(16))


def _make_id(rng: random.Random) -> str:
    return "setl_" + "".join(rng.choice("0123456789abcdef") for _ in range(12))


def _gross(rng: random.Random) -> int:
    # Realistic order-value clustering: round paise to whole rupees at common bands.
    base = rng.choice([149, 299, 499, 899, 1299, 2499, 4999, 9999, 14999, 24999])
    return base * 100


def _compute_net(rng: random.Random, gross: int) -> tuple[int, int, int, int, int]:
    """Return (fees, tax_gst, refunds, adjustments, net)."""
    fees = int(round(gross * rng.uniform(0.015, 0.025)))
    tax_gst = int(round(fees * 0.18))
    refunds = 0 if rng.random() < 0.7 else int(gross * rng.uniform(0.02, 0.08))
    adjustments = -int(gross * rng.uniform(0.01, 0.05)) if rng.random() < 0.15 else 0
    net = gross - fees - tax_gst - refunds + adjustments
    return fees, tax_gst, refunds, adjustments, net


def _n_transactions(rng: random.Random) -> int:
    return rng.randint(1, 40)


def generate_settlements(cfg: SeedConfig, rng: random.Random | None = None) -> list[SettlementScenario]:
    """Generate `batch_size` settlement scenarios preserving the category mix.

    Categories are assigned round-robin to hit the target ratios exactly
    (integer counts), so the composition is deterministic and testable.
    """
    rng = rng or _rng(cfg.seed)
    counts = _plan_counts(cfg)

    scenarios: list[SettlementScenario] = []

    # Deterministic base date; increments by 1 day per record (T+1 cadence).
    base_day = rng.randint(20000, 20800)  # epoch day ~ 2024-2026

    for category, n in counts.items():
        for _ in range(n):
            gross = _gross(rng)
            fees, tax, refunds, adj, net = _compute_net(rng, gross)
            day = base_day + len(scenarios)
            scenarios.append(
                SettlementScenario(
                    settlement_id=_make_id(rng),
                    utr=_make_utr(rng),
                    settlement_date=_day_to_iso(day),
                    no_of_transactions=_n_transactions(rng),
                    gross_amount=gross,
                    fees=fees,
                    tax_gst=tax,
                    refunds_deducted=refunds,
                    adjustments=adj,
                    net_amount=net,
                    status="processed",
                    bank_account_last4=str(rng.randint(1000, 9999)),
                    category=category,
                )
            )

    _assign_batch_groups(scenarios, counts.get("batched", 0))
    # Orphan settlements: still have a record but no bank line (true exception).
    for s in scenarios:
        if s.category == "orphan":
            s.intended_match = False
        if s.category == "ambiguous":
            s.intended_match = True

    return scenarios


def _day_to_iso(epoch_day: int) -> str:
    from datetime import date

    d = date.fromordinal(epoch_day)
    return d.isoformat()


def _plan_counts(cfg: SeedConfig) -> dict[str, int]:
    """Convert ratios to exact integer counts that sum to batch_size."""
    total = cfg.batch_size
    ratios = cfg.ratios
    counts: dict[str, int] = {}
    allocated = 0
    for key in ("exact", "fuzzy", "batched", "ambiguous", "orphan"):
        if key == "orphan":
            counts[key] = total - allocated  # remainder
        else:
            counts[key] = int(round(total * ratios[key]))
        allocated += counts[key]
    return counts


def _assign_batch_groups(scenarios: list[SettlementScenario], n_batched: int) -> None:
    """Group 'batched' settlements so several share a single bank line.

    We simply tag all batched settlements as one group; the statement generator
    will produce one aggregated credit for them. To keep it interesting, split
    them into groups of 2-3 sharing an aggregated bank line.
    """
    batched = [s for s in scenarios if s.category == "batched"]
    groups: list[list[SettlementScenario]] = []
    i = 0
    while i < len(batched):
        size = 3 if len(batched) - i >= 3 else len(batched) - i
        groups.append(batched[i : i + size])
        i += size
    for grp in groups:
        ids = [s.settlement_id for s in grp]
        for s in grp:
            s.batch_group = list(ids)
