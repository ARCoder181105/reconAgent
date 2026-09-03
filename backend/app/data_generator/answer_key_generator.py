"""Hidden answer-key generation.

Produces the ground-truth mapping used ONLY by the offline scoring script.
The structure:

    {
      "settlements": {
          "<settlement_id>": {"line_id": "<bl_xxxxx>" | null, "category": "..."},
          ...
      },
      "orphan_lines": ["<bl_xxxxx>", ...],
      "composition": {"exact": n, "fuzzy": n, "batched": n, "ambiguous": n, "orphan": n}
    }

`null` line_id means the settlement has no bank line (not-credited / true exception).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from backend.app.data_generator.generate_settlements import SettlementScenario
from backend.app.data_generator.generate_statement import BankLine


def build_answer_key(
    scenarios: Iterable[SettlementScenario],
    lines: Iterable[BankLine],
) -> dict:
    """Build the answer-key dict from the matched scenarios and bank lines."""
    settlements_map: dict[str, dict] = {}
    for s in scenarios:
        settlements_map[s.settlement_id] = {
            "line_id": None,
            "category": s.category,
            "net_amount": s.net_amount,
            "settlement_date": s.settlement_date,
        }

    orphan_lines: list[str] = []
    # Map bank lines back to their settlement(s) using ground-truth markers.
    for line in lines:
        if line.batch_settlement_ids:
            for sid in line.batch_settlement_ids:
                settlements_map[sid]["line_id"] = line.line_id
        elif line.settlement_id:
            if line.settlement_id in settlements_map:
                settlements_map[line.settlement_id]["line_id"] = line.line_id
        else:
            orphan_lines.append(line.line_id)

    return {
        "settlements": settlements_map,
        "orphan_lines": sorted(orphan_lines),
        "composition": _count(scenarios),
    }


def _count(scenarios: Iterable[SettlementScenario]) -> dict[str, int]:
    from collections import Counter

    return dict(Counter(s.category for s in scenarios))


def write_answer_key(answer_key: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(answer_key, indent=2), encoding="utf-8")
