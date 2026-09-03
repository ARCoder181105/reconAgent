"""Iteration 07: full-API integration test (httpx TestClient).

Exercises the maker/checker event-sourced workflow end to end against an
in-memory DB by overriding the ``get_session`` dependency.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, init_db
from backend.app.db import get_session
from backend.app.main import app

MED = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # share one in-memory DB across the TestClient thread
)
TestingSession = sessionmaker(bind=MED, autoflush=False, expire_on_commit=False)


def _override_session():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_session] = _override_session


@pytest.fixture(autouse=True)
def _fresh_db():
    init_db(MED)
    yield
    Base.metadata.drop_all(bind=MED)
    Base.metadata.create_all(bind=MED)


@pytest.fixture()
def client():
    return TestClient(app)


def test_full_maker_checker_workflow(client):
    # --- generate + run ---
    r = client.post("/api/run-reconciliation", params={"seed": 42})
    assert r.status_code == 200, r.text
    report = r.json()["report"]
    assert report["total_settlements"] > 0
    assert report["matched_settlements"] >= 10

    # --- report matches pipe ---
    assert client.get("/health").json()["status"] == "ok"

    # --- fetch open exceptions ---
    excs = client.get("/api/exceptions", params={"status": "open"}).json()
    assert excs, "expected open exceptions"

    # pick a review-tier exception that has both a line and a settlement
    candidate = next(e for e in excs if e["settlement_id"] and e["line_id"])
    exc_id = candidate["exception_id"]

    # --- maker resolves (proposes) ---
    r = client.post(
        f"/api/exceptions/{exc_id}/resolve",
        json={"maker_id": "alice", "action": "confirm", "resolution_data": {"note": "ok"}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "pending_approval"

    # pending-approval list reflects the maker submission
    pend = client.get("/api/exceptions/pending-approval").json()
    assert any(e["exception_id"] == exc_id for e in pend)

    # audit log records MAKER_PROPOSED
    events = client.get(f"/api/exceptions/{exc_id}/events").json()
    types = [ev["event_type"] for ev in events]
    assert types == ["CREATED", "MAKER_PROPOSED"]

    # --- maker cannot approve (only checker closes books) ---
    assert "approve" not in [ev["event_type"] for ev in events]

    # --- checker approves (closes) ---
    r = client.post(
        f"/api/exceptions/{exc_id}/approve",
        json={"checker_id": "bob", "decision": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "closed"

    events = client.get(f"/api/exceptions/{exc_id}/events").json()
    types = [ev["event_type"] for ev in events]
    assert "CHECKER_APPROVED" in types

    # closed exception no longer appears as pending
    pend = client.get("/api/exceptions/pending-approval").json()
    assert all(e["exception_id"] != exc_id for e in pend)

    # report now reflects verified records
    rr = client.get("/api/report").json()
    assert rr["verified_count"] >= 1


def test_checker_reject_reopens(client):
    client.post("/api/run-reconciliation", params={"seed": 42})
    excs = client.get("/api/exceptions", params={"status": "open"}).json()
    candidate = next(e for e in excs if e["settlement_id"] and e["line_id"])

    client.post(
        f"/api/exceptions/{candidate['exception_id']}/resolve",
        json={"maker_id": "alice", "action": "confirm"},
    )
    r = client.post(
        f"/api/exceptions/{candidate['exception_id']}/approve",
        json={"checker_id": "bob", "decision": False, "reason_text": "wrong"},
    )
    assert r.json()["status"] == "open"
    events = client.get(f"/api/exceptions/{candidate['exception_id']}/events").json()
    assert "CHECKER_REJECTED" in [ev["event_type"] for ev in events]


def test_approve_without_pending_is_conflict(client):
    client.post("/api/run-reconciliation", params={"seed": 42})
    excs = client.get("/api/exceptions", params={"status": "open"}).json()
    candidate = next(e for e in excs if e["settlement_id"] and e["line_id"])
    r = client.post(
        f"/api/exceptions/{candidate['exception_id']}/approve",
        json={"checker_id": "bob", "decision": True},
    )
    assert r.status_code == 409


def test_score_endpoint(client):
    r = client.get("/api/score", params={"seed": 42})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scorecard"]["precision"] == 1.0  # conservative engine: no FPs
    assert "penalized_score" in body["scorecard"]


def test_inspection_endpoints(client):
    client.post("/api/run-reconciliation", params={"seed": 42})
    assert client.get("/api/settlements").status_code == 200
    assert client.get("/api/bank-statement").status_code == 200
    assert len(client.get("/api/matches").json()) >= 10
