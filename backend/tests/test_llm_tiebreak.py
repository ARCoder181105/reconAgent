"""Iteration 08: async LLM tie-break tests (Stage 5).

Covers:
- schema-conformant JSON -> parsed decision
- malformed / chatty response -> graceful fallback
- mocked API exception -> fallback, no crash
- async queue drains and persists AI_TIEBREAK_SUGGESTED but does NOT auto-close
"""
from __future__ import annotations

import threading

import pytest

from backend.app.matcher import llm_tiebreak
from backend.app.services.llm_queue import (
    CONFIDENCE_IF_CONFIDENT,
    EVENT_AI_TIEBREAK_SUGGESTED,
    REVIEW_BAND_CEILING,
    TiebreakQueue,
    TiebreakTask,
)
from backend.constants import REASON_UTR_UNRESOLVED


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text


class _FakeClient:
    """Duck-typed Gemini client; returns a canned response."""

    def __init__(self, text: str = ""):
        self.text = text
        self.calls = []
        self.error: Exception | None = None
        self.chats = _FakeChats(self)


class _FakeChats:
    def __init__(self, owner):
        self._owner = owner

    def create(self, *, model, config=None):
        return _FakeChatSession(self._owner, model, config)


class _FakeChatSession:
    def __init__(self, owner, model, config):
        self._owner = owner
        self.model = model
        self.config = config

    def send_message(self, prompt):
        self._owner.calls.append({"model": self.model, "contents": prompt, "config": self.config})
        if self._owner.error is not None:
            raise self._owner.error
        return _FakeResponse(self._owner.text)


_LINE = {
    "line_id": "bl_00001",
    "description": "NEFT-1597813219E1P-RAZORPAY",
    "ref_no": "",
    "credit_paise": 500000,
    "txn_date": "2026-09-01",
}
_CANDIDATES = [
    {"settlement_id": "setl_1", "net_amount": 500000, "settlement_date": "2026-09-01"},
    {"settlement_id": "setl_2", "net_amount": 499999, "settlement_date": "2026-09-01"},
]


# --------------------------------------------------------------------------- #
# parse_tiebreak_response
# --------------------------------------------------------------------------- #

def test_parse_schema_conformant_json():
    text = (
        '{"match": true, "settlement_id": "setl_1", '
        '"confidence": 90, "reasoning": "amount matches exactly"}'
    )
    d = llm_tiebreak.parse_tiebreak_response(text)
    assert d is not None
    assert d.match is True
    assert d.settlement_id == "setl_1"
    assert d.confidence == 90
    assert d.reasoning == "amount matches exactly"
    assert d.source == llm_tiebreak.SOURCE_LLM


def test_parse_tolerates_json_fence():
    text = '```json\n{"match": false, "settlement_id": null, ' \
           '"confidence": 0, "reasoning": "no fit"}\n```'
    d = llm_tiebreak.parse_tiebreak_response(text)
    assert d is not None
    assert d.match is False
    assert d.settlement_id is None


def test_parse_rejects_chatty_prose():
    d = llm_tiebreak.parse_tiebreak_response(
        "I think maybe the line matches setl_1 because the amounts look close. "
        "You should probably go with that one."
    )
    assert d is None


def test_parse_rejects_non_json():
    assert llm_tiebreak.parse_tiebreak_response("not json at all") is None


def test_parse_rejects_missing_fields():
    # confidence missing -> not conformant -> None
    d = llm_tiebreak.parse_tiebreak_response(
        '{"match": true, "settlement_id": "setl_1", "reasoning": "x"}'
    )
    assert d is None


def test_parse_clamps_confidence_range():
    d = llm_tiebreak.parse_tiebreak_response(
        '{"match": false, "settlement_id": null, "confidence": 500, "reasoning": ""}'
    )
    assert d.confidence == 100


def test_parse_empty_string_returns_none():
    assert llm_tiebreak.parse_tiebreak_response("") is None


# --------------------------------------------------------------------------- #
# run_tiebreak
# --------------------------------------------------------------------------- #

def test_run_tiebreak_schema_conformant():
    client = _FakeClient(
        '{"match": true, "settlement_id": "setl_1", '
        '"confidence": 85, "reasoning": "exact amount"}'
    )
    d = llm_tiebreak.run_tiebreak(client, _LINE, _CANDIDATES, "fake-model")
    assert d.match is True
    assert d.settlement_id == "setl_1"
    assert d.confidence == 85
    assert d.source == llm_tiebreak.SOURCE_LLM


def test_run_tiebreak_malformed_falls_back():
    client = _FakeClient("please match the first one, it is best")
    d = llm_tiebreak.run_tiebreak(client, _LINE, _CANDIDATES, "fake-model")
    # Graceful degradation, never a crash and never a fabricated match.
    assert d.match is False
    assert d.settlement_id is None
    assert d.source == llm_tiebreak.SOURCE_FALLBACK


def test_run_tiebreak_api_exception_falls_back():
    client = _FakeClient()
    client.error = RuntimeError("upstream rate limit")
    d = llm_tiebreak.run_tiebreak(client, _LINE, _CANDIDATES, "fake-model")
    assert d.match is False
    assert d.source == llm_tiebreak.SOURCE_FALLBACK


def test_run_tiebreak_uses_structured_output_config():
    client = _FakeClient('{"match": false, "settlement_id": null, "confidence": 0, "reasoning": ""}')
    llm_tiebreak.run_tiebreak(client, _LINE, _CANDIDATES, "fake-model")
    cfg = client.calls[0]["config"]
    assert cfg["response_mime_type"] == "application/json"
    assert "response_schema" in cfg
    assert cfg["response_schema"].required == ["match", "settlement_id", "confidence", "reasoning"]


# --------------------------------------------------------------------------- #
# build_tiebreak_prompt
# --------------------------------------------------------------------------- #

def test_build_prompt_includes_candidates():
    prompt = llm_tiebreak.build_tiebreak_prompt(_LINE, _CANDIDATES)
    assert "setl_1" in prompt
    assert "setl_2" in prompt


def test_build_prompt_no_candidates():
    prompt = llm_tiebreak.build_tiebreak_prompt(_LINE, [])
    assert "match=false" in prompt


# --------------------------------------------------------------------------- #
# TiebreakQueue (async drain + event sourcing governance)
# --------------------------------------------------------------------------- #

def _make_mem_sessions():
    """Return (write_session, factory_for_worker) on a private in-memory DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from backend.app.db import Base, init_db

    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(eng)
    S = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    write = S()
    return write, lambda: S(), eng


def test_queues_drains_and_persists_event_but_does_not_close():
    """Drain one task; must append AI_TIEBREAK_SUGGESTED and stay open."""
    from backend.app.models import Exception as ExceptionModel

    db_session, worker_factory, eng = _make_mem_sessions()

    exc = ExceptionModel(
        reason_code=REASON_UTR_UNRESOLVED,
        line_id="bl_00001",
        confidence=0,
        candidates_json='[]',
        status="open",
    )
    db_session.add(exc)
    db_session.commit()
    exc_id = exc.exception_id

    sentinel = {"called": False}

    def fake_run(client, task, model):
        sentinel["called"] = True
        return llm_tiebreak.LLMDecision(
            match=True,
            settlement_id="setl_1",
            confidence=90,
            reasoning="amount matches",
        )

    queue = TiebreakQueue(
        api_key="",
        model="fake-model",
        run_fn=fake_run,
        gen_factory=lambda key, provider="", base_url="": object(),  # dummy client; fake_run doesn't use it
        session_factory=worker_factory,
    )
    queue.enqueue(
        TiebreakTask(
            exception_id=exc_id,
            line=_LINE,
            candidates=_CANDIDATES,
            reason_code=REASON_UTR_UNRESOLVED,
        )
    )
    queue.start()
    _wait_drained(queue)

    assert sentinel["called"] is True
    assert queue.processed() == 1
    assert queue.failed() == 0
    assert queue.pending() == 0

    check = worker_factory()
    try:
        row = check.get(ExceptionModel, exc_id)
        events = list(row.events)
        types = [ev.event_type for ev in events]
        assert EVENT_AI_TIEBREAK_SUGGESTED in types
        # Governance: the LLM can lift confidence but never into auto-close
        # (>=85) and NEVER closes the exception.
        assert row.status == "open"
        assert row.confidence <= REVIEW_BAND_CEILING
        assert row.confidence == CONFIDENCE_IF_CONFIDENT
    finally:
        check.close()


def test_queue_records_failures_without_crash():
    from backend.app.models import Exception as ExceptionModel

    db_session, worker_factory, eng = _make_mem_sessions()
    exc = ExceptionModel(reason_code=REASON_UTR_UNRESOLVED, line_id="bl_x", status="open")
    db_session.add(exc)
    db_session.commit()

    def failing_run(client, task, model):
        raise RuntimeError("boom")

    queue = TiebreakQueue(
        api_key="",
        model="fake-model",
        run_fn=failing_run,
        session_factory=worker_factory,
    )
    queue.enqueue(TiebreakTask(exception_id=exc.exception_id, line=_LINE, candidates=_CANDIDATES))
    queue.start()
    _wait_drained(queue)

    assert queue.failed() == 1
    assert queue.processed() == 0


def test_client_construction_failure_persists_fallback_not_stranded():
    """Bad/missing GEMINI_API_KEY must NOT kill the worker.

    A gen_factory that raises (simulating an invalid key) should degrade to the
    deterministic fallback decision — persisted as an AI_TIEBREAK_SUGGESTED
    event with source=fallback — and still be accounted, instead of leaving the
    task stranded forever with nothing persisted.
    """
    import json

    from backend.app.models import Exception as ExceptionModel

    db_session, worker_factory, eng = _make_mem_sessions()

    def add_exc(line_id):
        exc = ExceptionModel(
            reason_code=REASON_UTR_UNRESOLVED, line_id=line_id, status="open"
        )
        db_session.add(exc)
        db_session.commit()
        return exc.exception_id

    id_a = add_exc("bl_a")
    id_b = add_exc("bl_b")

    def boom_factory(api_key, provider="", base_url=""):
        raise RuntimeError("bad GEMINI_API_KEY")

    queue = TiebreakQueue(
        api_key="",
        model="fake-model",
        gen_factory=boom_factory,
        session_factory=worker_factory,
    )
    queue.enqueue(TiebreakTask(exception_id=id_a, line=_LINE, candidates=_CANDIDATES))
    queue.enqueue(TiebreakTask(exception_id=id_b, line=_LINE, candidates=_CANDIDATES))
    queue.start()
    _wait_drained(queue)

    assert queue.pending() == 0
    assert queue.failed() == 2
    assert queue.processed() == 0

    check = worker_factory()
    try:
        for exc_id in (id_a, id_b):
            row = check.get(ExceptionModel, exc_id)
            events = [ev for ev in row.events]
            assert len(events) == 1
            ev = events[0]
            assert ev.event_type == EVENT_AI_TIEBREAK_SUGGESTED
            data = json.loads(ev.resolution_data or "{}")
            assert data.get("source") == llm_tiebreak.SOURCE_FALLBACK
            assert row.status == "open"
    finally:
        check.close()


def _wait_drained(queue: TiebreakQueue, timeout: float = 5.0) -> None:
    """Block until the worker has consumed all tasks (or timed out)."""
    import time

    end = time.time() + timeout
    while time.time() < end:
        if queue.pending() == 0 and queue._worker is not None and not queue._worker.is_alive():
            return
        if queue.pending() == 0 and queue.processed() + queue.failed() > 0 \
                and not queue._worker.is_alive():
            return
        time.sleep(0.01)
    # Force-join as a last resort.
    if queue._worker is not None:
        queue._worker.join(timeout=1.0)
