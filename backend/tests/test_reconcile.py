"""Iteration 05: reconcile orchestration tests."""
from __future__ import annotations

from collections import Counter

import pandas as pd

from backend.app.data_generator.generator import GeneratedData, generate
from backend.app.data_generator.generator import write_settlements_csv, write_statement_csv
from backend.app.matcher.reconcile import reconcile


def _rows(dataset: GeneratedData, tmp_path) -> tuple[list[dict], list[dict]]:
    """Write CSV artifacts and read them back as raw dicts.

    Reading via CSV is the real contract: the reconciler sees only the public
    columns and never the hidden category/answer-key markers.
    """
    write_settlements_csv(dataset.scenarios, tmp_path / "settlements.csv")
    write_statement_csv(dataset.lines, tmp_path / "bank_statement.csv")
    sett_df = pd.read_csv(tmp_path / "settlements.csv")
    stmt_df = pd.read_csv(tmp_path / "bank_statement.csv")
    return sett_df.to_dict("records"), stmt_df.to_dict("records")


def test_reconcile_full_batch_no_answer_key(tmp_path):
    dataset = generate()

    settlements, lines = _rows(dataset, tmp_path)

    # Ensure reconcile sees NO category markers (they are not CSV columns).
    for s in settlements:
        assert "category" not in s
        assert "intended_match" not in s

    for l in lines:
        assert "settlement_id" not in l
        assert "batch_settlement_ids" not in l

    result = reconcile(settlements, lines)

    assert result.matches
    assert result.exceptions
    assert result.report["total_settlements"] > 0

    # Every bank line is either matched or excepted (full batch, no pre-filter).
    matched_line_ids = {m.line_id for m in result.matches}
    excepted_line_ids = {e.line_id for e in result.exceptions if e.line_id}
    covered = matched_line_ids | excepted_line_ids
    assert covered == {l["line_id"] for l in lines}, "every credit & debit line covered"

    # Stages used are canonical.
    for m in result.matches:
        assert m.stage in {"exact", "fuzzy_utr", "amount_date", "batch_sum", "llm_tiebreak"}

    # Report fields present.
    for key in (
        "total_settlements",
        "total_bank_lines",
        "matched_settlements",
        "auto_matched",
        "match_rate",
        "review_rate",
        "exception_rate",
    ):
        assert key in result.report

    assert result.report["matched_settlements"] == len(
        {m.settlement_id for m in result.matches}
    )
    assert result.report["auto_matched"] == len(
        {m.settlement_id for m in result.matches if m.confidence >= 85}
    )


def test_reconcile_resolves_exact_and_batched(tmp_path):
    dataset = generate()
    settlements, lines = _rows(dataset, tmp_path)
    result = reconcile(settlements, lines)

    stages = Counter(m.stage for m in result.matches)

    # Generator produces exact + batched scenarios; both resolve.
    assert "exact" in stages
    assert "batch_sum" in stages
    assert "fuzzy_utr" in stages
    assert stages["exact"] >= 10

    # Batched: one line -> multiple settlements sharing the same line_id.
    line_to_settlements: dict[str, list[str]] = {}
    for m in result.matches:
        if m.stage == "batch_sum":
            line_to_settlements.setdefault(m.line_id, []).append(m.settlement_id)
    for lid, sids in line_to_settlements.items():
        assert len(sids) >= 2, "a batch credit must bind >=2 settlements"


def test_reconcile_flags_orphan_settlements(tmp_path):
    dataset = generate()
    settlements, lines = _rows(dataset, tmp_path)
    result = reconcile(settlements, lines)

    orphan_exceptions = [
        e for e in result.exceptions
        if e.settlement_id and not e.line_id and e.reason_code == "NO_CANDIDATE"
    ]
    # Generator creates deliberately not-credited (orphan) settlements.
    assert orphan_exceptions, "expected at least one not-credited settlement exception"


def test_reconcile_honest_on_utr_mangled():
    # Build one settlement + one truly unmatchable line manually.
    settlements = [
        {
            "settlement_id": "setl_z",
            "utr": "AAAAAAAAAAAAAAAA",
            "settlement_date": "2026-09-01",
            "net_amount": 100000,
            "gross_amount": 110000,
            "fees": 10000,
            "tax_gst": 1000,
            "refunds_deducted": 0,
            "adjustments": 0,
            "status": "processed",
            "bank_account_last4": "1234",
        }
    ]
    lines = [
        {
            "line_id": "bl_z",
            "txn_date": "2026-09-01",
            "value_date": "",
            "description": "NEFT-BBBBBBBBBBBBBBBB",  # different UTR, same amount
            "ref_no": "",
            "debit": None,
            "credit": 5000.00,  # amount differs so amount+date cannot guess
            "balance": None,
            "bank_name": "HDFC",
        }
    ]
    result = reconcile(settlements, lines)
    # The credit line cannot be matched (UTR + amount differ); must surface.
    assert all(m.line_id != "bl_z" for m in result.matches)
    assert any(e.line_id == "bl_z" for e in result.exceptions)
