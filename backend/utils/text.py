"""Text canonicalization and token extraction helpers."""
from __future__ import annotations

import re

# A UTR-like token: 12-18 alphanumeric run (generator emits 16 chars).
UTR_TOKEN_RE = re.compile(r"[A-Z0-9]{12,18}")


def normalize_text(value) -> str:
    """Uppercase + strip whitespace. Returns '' for None/blank."""
    if not value:
        return ""
    return str(value).strip().upper()


def upper_strip(value) -> str:
    """Alias kept for readability where 'uppercase + trim' is the intent."""
    return normalize_text(value)


def extract_utr_tokens(text: str) -> list[str]:
    """Return UTR-like tokens found in a freetext string (uppercased)."""
    if not text:
        return []
    return UTR_TOKEN_RE.findall(text.upper())
