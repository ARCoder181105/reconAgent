"""Money conversion helpers.

All monetary values in ReconAgent are integer paise internally; the bank
statement stores rupees as floats. These helpers are the single place those
conversions happen.
"""
from __future__ import annotations

import math
import re

# Matches currency-symbol-prefixed numbers with optional thousands separators.
_NUM_STRIP = re.compile(r"[^\d.,-]")

PAISE_PER_RUPEE = 100


def rupees_to_paise(value) -> int | None:
    """Convert a money value (float rupees or formatted string) to integer paise.

    Handles strings like "1,234.56", "₹1,234.56", or already-numeric floats.
    Returns None for blank/None/NaN input.
    """
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        num = float(value)
    else:
        cleaned = _NUM_STRIP.sub("", str(value))
        cleaned = cleaned.replace(",", "")  # remove thousands separators
        try:
            num = float(cleaned)
        except ValueError:
            return None
    return int(round(num * PAISE_PER_RUPEE))


def paise_to_rupees(paise: int | None) -> float | None:
    """Convert integer paise to a 2-dp rupees float (or None for None)."""
    if paise is None:
        return None
    return round(paise / PAISE_PER_RUPEE, 2)
