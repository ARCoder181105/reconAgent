"""SQLAlchemy ORM models for ReconAgent.

Naming and columns mirror `docs/master-design.md` §9. Amounts are integer paise.
`ExceptionEvent` is the append-only system of record for exception governance;
`Exception.status` is only a denormalized projection cache for fast queue reads.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Settlement(Base):
    """Structured gateway-side record: one row per settlement batch."""

    __tablename__ = "settlements"

    settlement_id: Mapped[str] = mapped_column(String, primary_key=True)
    utr: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    settlement_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # ISO YYYY-MM-DD
    no_of_transactions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gross_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # paise
    fees: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # paise
    tax_gst: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # paise
    refunds_deducted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # paise
    adjustments: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # paise, can be negative
    net_amount: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # paise
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # processed/on_hold/reversed
    bank_account_last4: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class BankStatement(Base):
    """Messy bank-side record: one row per statement line.

    ``line_id`` is a stable String key assigned by the generator (e.g. ``bl_00001``)
    so the hidden answer key can reference the same identifier as the matcher DB.
    """

    __tablename__ = "bank_statement"

    line_id: Mapped[str] = mapped_column(String, primary_key=True)
    txn_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    value_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ref_no: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    debit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    credit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    balance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bank_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Match(Base):
    """A closed settlement <-> bank line match produced by the pipeline."""

    __tablename__ = "matches"

    match_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    settlement_id: Mapped[str] = mapped_column(
        ForeignKey("settlements.settlement_id"), nullable=False
    )
    line_id: Mapped[str] = mapped_column(
        ForeignKey("bank_statement.line_id"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String, nullable=False)  # exact/fuzzy_utr/amount_date/batch_sum/llm_tiebreak
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    settlement: Mapped[Settlement] = relationship()
    statement_line: Mapped[BankStatement] = relationship()


class Exception(Base):
    """An exception routed to human review.

    status is a projection cache ('open'/'closed'); the authoritative history is
    the ExceptionEvent append-only log.
    """

    __tablename__ = "exceptions"

    exception_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    settlement_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    line_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reason_code: Mapped[str] = mapped_column(String, nullable=False)
    confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    candidates_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)  # projection
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    events: Mapped[list["ExceptionEvent"]] = relationship(
        back_populates="exception", cascade="all, delete-orphan"
    )


class ExceptionEvent(Base):
    """Append-only event log for exception governance. System of record.

    event_type ∈ {CREATED, MAKER_PROPOSED, CHECKER_APPROVED, CHECKER_REJECTED}.
    """

    __tablename__ = "exception_events"

    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exception_id: Mapped[int] = mapped_column(
        ForeignKey("exceptions.exception_id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    # event_type ∈ {CREATED, MAKER_PROPOSED, CHECKER_APPROVED, CHECKER_REJECTED,
    #              AI_TIEBREAK_SUGGESTED} (plain String; no DB constraint).
    maker_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    checker_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolution_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    exception: Mapped[Exception] = relationship(back_populates="events")
