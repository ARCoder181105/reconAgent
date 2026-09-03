"""Seed configuration for the synthetic data generator.

Controls composition ratios, record counts, and the deterministic seed so a
given seed always regenerates the same batch. See `docs/master-design.md` §3.3.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeedConfig:
    """Tunables for the generator."""

    seed: int = 42
    batch_size: int = 60            # number of settlement records (>=50)

    # Composition of settlement records by category (sum ~ 1.0)
    true_exact_ratio: float = 0.40   # easy: exact UTR substring
    true_fuzzy_ratio: float = 0.20   # medium: truncated / mid-string UTR
    true_batchedup_ratio: float = 0.10  # hard: one bank line = sum of multiple settlements
    ambiguous_ratio: float = 0.10    # ambiguous-but-resolvable
    orphan_exception_ratio: float = 0.20  # true exceptions: unmatchable bank lines

    # Tolerance (paise) for amount matching
    amount_tolerance_paise: int = 100  # ± ₹1 = 100 paise

    # Bank-side wire fee to simulate "off-by-fee" records (paise)
    off_by_fee_paise: int = 400        # ₹4

    @property
    def ratios(self) -> dict[str, float]:
        return {
            "exact": self.true_exact_ratio,
            "fuzzy": self.true_fuzzy_ratio,
            "batched": self.true_batchedup_ratio,
            "ambiguous": self.ambiguous_ratio,
            "orphan": self.orphan_exception_ratio,
        }

    def validate(self) -> None:
        total = sum(self.ratios.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"ratios must sum to 1.0, got {total:.4f}")
        if self.batch_size < 50:
            raise ValueError("batch_size must be >= 50")


def build_config(**overrides) -> SeedConfig:
    cfg = SeedConfig(**overrides)
    cfg.validate()
    return cfg
