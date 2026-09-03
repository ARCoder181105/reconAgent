"""Iteration 01: DB layer smoke tests.

Verifies schema initialization and basic CRUD for the models defined in
`backend/app/models.py`.
"""
from __future__ import annotations

from sqlalchemy import inspect

from backend.app.models import (
    BankStatement,
    Exception as ExceptionModel,
    ExceptionEvent,
    Match,
    Settlement,
)


def test_all_tables_created(db_session):
    inspector = inspect(db_session.bind)
    tables = set(inspector.get_table_names())
    assert {
        "settlements",
        "bank_statement",
        "matches",
        "exceptions",
        "exception_events",
    } <= tables


def test_settlement_insert_and_read(db_session):
    s = Settlement(
        settlement_id="setl_test001",
        utr="1597813219E1PQ6W",
        settlement_date="2026-09-01",
        no_of_transactions=12,
        gross_amount=100000,
        fees=2000,
        tax_gst=360,
        refunds_deducted=0,
        adjustments=0,
        net_amount=97640,
        status="processed",
        bank_account_last4="1234",
    )
    db_session.add(s)
    db_session.flush()

    row = db_session.get(Settlement, "setl_test001")
    assert row is not None
    assert row.net_amount == 97640
    assert row.gross_amount - row.fees - row.tax_gst - row.refunds_deducted + row.adjustments == row.net_amount


def test_bank_statement_insert(db_session):
    line = BankStatement(
        txn_date="01-09-2026",
        value_date=None,
        description="NEFT-1597813219E1P-RAZORPAY SOFTWARE PVT LTD",
        ref_no="",
        credit=1234.56,
        debit=None,
        balance=98765.43,
        bank_name="HDFC",
    )
    db_session.add(line)
    db_session.flush()
    assert line.line_id is not None


def test_match_foreign_keys(db_session):
    s = Settlement(settlement_id="setl_x", net_amount=5000)
    b = BankStatement(description="x", credit=50.0)
    db_session.add_all([s, b])
    db_session.flush()

    m = Match(settlement_id=s.settlement_id, line_id=b.line_id, stage="exact", confidence=100)
    db_session.add(m)
    db_session.flush()
    assert m.match_id is not None


def test_exception_event_foreign_key(db_session):
    e = ExceptionModel(reason_code="NO_CANDIDATE", status="open")
    db_session.add(e)
    db_session.flush()

    ev = ExceptionEvent(exception_id=e.exception_id, event_type="CREATED")
    db_session.add(ev)
    db_session.flush()
    assert ev.event_id is not None
    assert e.events[0].event_type == "CREATED"
