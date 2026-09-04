"""Pydantic schemas for API request/response and internal DTOs.

Core schemas live here from the start; they expand in Iteration 07 when the
FastAPI layer lands.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Settlement ---
class SettlementOut(ORMModel):
    settlement_id: str
    utr: Optional[str] = None
    settlement_date: Optional[str] = None
    no_of_transactions: Optional[int] = None
    gross_amount: Optional[int] = None
    fees: Optional[int] = None
    tax_gst: Optional[int] = None
    refunds_deducted: Optional[int] = None
    adjustments: Optional[int] = None
    net_amount: Optional[int] = None
    status: Optional[str] = None
    bank_account_last4: Optional[str] = None


# --- Bank statement ---
class BankStatementOut(ORMModel):
    line_id: str
    txn_date: Optional[str] = None
    value_date: Optional[str] = None
    description: Optional[str] = None
    ref_no: Optional[str] = None
    debit: Optional[float] = None
    credit: Optional[float] = None
    balance: Optional[float] = None
    bank_name: Optional[str] = None


# --- Match / audit trail ---
class MatchOut(ORMModel):
    match_id: int
    settlement_id: str
    line_id: str
    stage: str
    confidence: int
    resolved_at: datetime
    net_ok: bool = True  # passive: does gross - fees - tax_gst ≈ net_amount?


# --- Exception ---
class Candidate:
    """Lightweight candidate descriptor used in candidates_json."""

    __slots__ = ("settlement_id", "line_id", "score", "stage")

    def __init__(self, settlement_id: str, line_id: str, score: float, stage: str):
        self.settlement_id = settlement_id
        self.line_id = line_id
        self.score = score
        self.stage = stage

    def to_dict(self) -> dict:
        return {
            "settlement_id": self.settlement_id,
            "line_id": self.line_id,
            "score": self.score,
            "stage": self.stage,
        }


class ExceptionOut(ORMModel):
    exception_id: int
    settlement_id: Optional[str] = None
    line_id: Optional[str] = None
    reason_code: str
    confidence: Optional[int] = None
    candidates_json: Optional[str] = None
    status: str
    created_at: datetime


class ExceptionEventOut(ORMModel):
    event_id: int
    exception_id: int
    event_type: str
    maker_id: Optional[str] = None
    checker_id: Optional[str] = None
    resolution_data: Optional[str] = None
    reason_text: Optional[str] = None
    timestamp: datetime


# --- Request DTOs (maker/checker) ---
class ExceptionResolveIn(BaseModel):
    """Maker proposal. Only proposes; never closes."""
    maker_id: str
    action: str  # confirm | reject | override
    resolution_data: Optional[dict] = None


class ExceptionApproveIn(BaseModel):
    """Checker decision that closes (or re-opens) an exception."""
    checker_id: str
    decision: bool
    reason_text: Optional[str] = None


class GenerateResponse(BaseModel):
    seed: int
    settlements: int
    bank_lines: int


class RunResponse(BaseModel):
    report: dict


class ScoreResponse(BaseModel):
    run: dict
    scorecard: dict
