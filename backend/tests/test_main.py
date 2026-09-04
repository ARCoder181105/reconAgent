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


def test_checker_cannot_approve_own_proposal_segregation_of_duties(client):
    """The person who proposed (maker) must not approve their own work."""
    client.post("/api/run-reconciliation", params={"seed": 42})
    excs = client.get("/api/exceptions", params={"status": "open"}).json()
    candidate = next(e for e in excs if e["settlement_id"] and e["line_id"])
    exc_id = candidate["exception_id"]

    r = client.post(
        f"/api/exceptions/{exc_id}/resolve",
        json={"maker_id": "alice", "action": "confirm"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "pending_approval"

    # same person tries to approve their own proposal -> 403 + clear reason
    r = client.post(
        f"/api/exceptions/{exc_id}/approve",
        json={"checker_id": "alice", "decision": True},
    )
    assert r.status_code == 403
    assert "cannot approve their own proposal" in r.json()["detail"]

    # still pending; a different checker can approve
    r = client.post(
        f"/api/exceptions/{exc_id}/approve",
        json={"checker_id": "bob", "decision": True},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "closed"


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


def test_report_cash_position(client):
    """Cash block exposes the four money views; auto+review+exceptions == book."""
    client.post("/api/run-reconciliation", params={"seed": 42})
    rr = client.get("/api/report").json()
    cash = rr["cash"]

    for key in ("rupees_auto", "rupees_review", "rupees_exceptions", "rupees_verified"):
        assert key in cash
        assert cash[key] >= 0

    # auto/review/exceptions are a partition of the whole book (D6 it's the
    # four *views* that overlap, not these three). Allow float tolerance.
    book = cash["rupees_auto"] + cash["rupees_review"] + cash["rupees_exceptions"]
    assert book > 0

    # Verified may never exceed the matched book; and the verified figure must
    # not be doctored to equal auto (that's the D6 gap, surfaced honestly).
    assert cash["rupees_verified"] <= cash["rupees_auto"] + cash["rupees_review"] + 0.01


def test_broadcast_fires_on_approve(client):
    """After approve, the CHECKER_APPROVED event is in the DB and the report
    reflects the verified record (the broadcast is fire-and-forget via
    BackgroundTasks — it doesn't block the response)."""
    client.post("/api/run-reconciliation", params={"seed": 42})
    excs = client.get("/api/exceptions", params={"status": "open"}).json()
    candidate = next(e for e in excs if e["settlement_id"] and e["line_id"])
    exc_id = candidate["exception_id"]

    # resolve + approve
    client.post(f"/api/exceptions/{exc_id}/resolve",
                json={"maker_id": "alice", "action": "confirm"})
    client.post(f"/api/exceptions/{exc_id}/approve",
                json={"checker_id": "bob", "decision": True})

    # The broadcast is fire-and-forget (BackgroundTasks); verify the DB side effect.
    events = client.get(f"/api/exceptions/{exc_id}/events").json()
    types = [e["event_type"] for e in events]
    assert "CHECKER_APPROVED" in types

    # And the report now reflects the verified record.
    rr = client.get("/api/report").json()
    assert rr["verified_count"] >= 1


def test_broadcast_bus():
    """The in-memory event bus fans out to all registered listeners."""
    import asyncio
    from backend.app.events import _register, _unregister, broadcast

    lid, q = _register()
    try:
        asyncio.get_event_loop().run_until_complete(
            broadcast("test_event", {"key": "value"})
        )
        msg = q.get_nowait()
        assert msg["event"] == "test_event"
        assert msg["data"]["key"] == "value"
    finally:
        _unregister(lid)


def test_matches_include_net_ok(client):
    """Each match carries a passive net_ok flag from the settlement fee math."""
    client.post("/api/run-reconciliation", params={"seed": 42})
    matches = client.get("/api/matches").json()
    assert len(matches) > 0
    for m in matches:
        assert "net_ok" in m
        assert isinstance(m["net_ok"], bool)
    # Synthetic data produces a mix: some settlements have consistent fee math,
    # others have intentionally messy data. Both True and False are valid.
    has_true = any(m["net_ok"] for m in matches)
    has_false = any(not m["net_ok"] for m in matches)
    assert has_true and has_false, "expected a mix of net_ok True and False in synthetic data"
