"""Iteration 02: data generator tests.

Verifies composition, arithmetic, answer-key consistency, determinism, and that
the generated artifacts land on disk.
"""
from __future__ import annotations

import json

import pytest

from backend.app.data_generator.answer_key_generator import build_answer_key
from backend.app.data_generator.generator import generate, generate_to_disk
from backend.app.data_generator.seed_config import build_config


def _gen():
    cfg = build_config()
    return generate(cfg), cfg


def test_batch_size_at_least_50():
    data, cfg = _gen()
    assert len(data.scenarios) >= 50


def test_net_amount_arithmetic():
    data, _ = _gen()
    for s in data.scenarios:
        assert s.net_amount == s.gross_amount - s.fees - s.tax_gst - s.refunds_deducted + s.adjustments


def test_composition_preserved():
    data, cfg = _gen()
    total = len(data.scenarios)
    exact = sum(1 for s in data.scenarios if s.category == "exact")
    fuzzy = sum(1 for s in data.scenarios if s.category == "fuzzy")
    batched = sum(1 for s in data.scenarios if s.category == "batched")
    ambiguous = sum(1 for s in data.scenarios if s.category == "ambiguous")
    orphan = sum(1 for s in data.scenarios if s.category == "orphan")
    assert exact + fuzzy + batched + ambiguous + orphan == total
    # True matches dominate (~70%)
    true = exact + fuzzy + batched
    assert abs(true / total - 0.70) < 0.11


def test_batch_groups_share_one_line():
    data, _ = _gen()
    batched = [s for s in data.scenarios if s.category == "batched"]
    # Every batched settlement must reference a line via its group mapping.
    lines_by_id = {l.line_id: l for l in data.lines}
    answer = build_answer_key(data.scenarios, data.lines)
    for s in batched:
        sid = s.settlement_id
        line_id = answer["settlements"][sid].get("line_id")
        assert line_id is not None
        assert line_id in lines_by_id


def test_answer_key_consistent():
    data, _ = _gen()
    answer = build_answer_key(data.scenarios, data.lines)
    # Every settlement key exists.
    assert len(answer["settlements"]) == len(data.scenarios)
    # Orphan lines are actual generated lines with no settlement.
    line_ids = {l.line_id for l in data.lines}
    for lid in answer["orphan_lines"]:
        assert lid in line_ids
    # Any non-null line references a real line.
    for sid, meta in answer["settlements"].items():
        if meta["line_id"] is not None:
            assert meta["line_id"] in line_ids


def test_deterministic():
    d1, _ = _gen()
    d2, _ = _gen()
    assert [(_line_key(l)) for l in d1.lines] == [(_line_key(l)) for l in d2.lines]
    assert [s.settlement_id for s in d1.scenarios] == [s.settlement_id for s in d2.scenarios]


def _line_key(line):
    return (line.line_id, line.description, line.credit, line.settlement_id, tuple(line.batch_settlement_ids))


def test_generate_to_disk(tmp_path):
    data = generate_to_disk(out_dir=tmp_path)
    assert (tmp_path / "settlements.csv").exists()
    assert (tmp_path / "bank_statement.csv").exists()
    assert (tmp_path / "answer_key.json").exists()
    key = json.loads((tmp_path / "answer_key.json").read_text())
    assert "settlements" in key
    assert "orphan_lines" in key
