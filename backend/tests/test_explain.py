"""Tests for the two-layer exception explanation system."""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from backend.app.services.explain import (
    ExplanationInput,
    _parse_explain_response,
    build_explain_prompt,
    explain_exception,
    explain_with_llm,
)


# ---------------------------------------------------------------------------
# Part 1 — Deterministic explanation templates (unit tests, no DB)
# ---------------------------------------------------------------------------

class TestExplainNoCandidate:
    def test_credit_with_no_match(self):
        inp = ExplanationInput(
            reason_code="NO_CANDIDATE",
            confidence=100,
            settlement_id=None,
            line_id="bl_00042",
            candidates=[],
            credit_paise=500000,
            txn_date="2025-04-10",
        )
        text = explain_exception(inp)
        assert "5,000" in text
        assert "2025-04-10" in text
        assert "No settlement" in text

    def test_debit_no_settlement(self):
        inp = ExplanationInput(
            reason_code="NO_CANDIDATE",
            confidence=100,
            settlement_id=None,
            line_id="bl_00099",
            candidates=[],
            credit_paise=None,  # debit line
            txn_date="2025-04-10",
        )
        text = explain_exception(inp)
        assert "debit" in text.lower()

    def test_settlement_not_in_bank(self):
        inp = ExplanationInput(
            reason_code="NO_CANDIDATE",
            confidence=100,
            settlement_id="setl_001",
            line_id=None,
            candidates=[],
        )
        text = explain_exception(inp)
        assert "setl_001" in text
        assert "not found" in text.lower()


class TestExplainMultiple:
    def test_multiple_with_credit(self):
        inp = ExplanationInput(
            reason_code="MULTIPLE_CANDIDATES",
            confidence=60,
            settlement_id=None,
            line_id="bl_00010",
            candidates=[
                {"settlement_id": "setl_001"},
                {"settlement_id": "setl_002"},
                {"settlement_id": "setl_003"},
            ],
            credit_paise=750000,
            txn_date="2025-04-12",
        )
        text = explain_exception(inp)
        assert "3" in text
        assert "setl_001" in text
        assert "human call" in text.lower()

    def test_multiple_without_credit(self):
        inp = ExplanationInput(
            reason_code="MULTIPLE_CANDIDATES",
            confidence=60,
            settlement_id=None,
            line_id="bl_00010",
            candidates=[
                {"settlement_id": "setl_001"},
                {"settlement_id": "setl_002"},
            ],
        )
        text = explain_exception(inp)
        assert "2" in text
        assert "setl_001" in text


class TestExplainAmountMismatch:
    def test_with_candidate_amount(self):
        inp = ExplanationInput(
            reason_code="AMOUNT_MISMATCH",
            confidence=40,
            settlement_id=None,
            line_id="bl_00055",
            candidates=[
                {"settlement_id": "setl_010", "net_amount": 500000},
            ],
            credit_paise=480000,
            txn_date="2025-04-11",
        )
        text = explain_exception(inp)
        assert "setl_010" in text
        assert "gap" in text.lower()

    def test_no_candidates(self):
        inp = ExplanationInput(
            reason_code="AMOUNT_MISMATCH",
            confidence=0,
            settlement_id=None,
            line_id="bl_00060",
            candidates=[],
            credit_paise=300000,
            txn_date="2025-04-11",
        )
        text = explain_exception(inp)
        assert "3,000" in text


class TestExplainUtrUnresolved:
    def test_with_candidate(self):
        inp = ExplanationInput(
            reason_code="UTR_UNRESOLVED",
            confidence=30,
            settlement_id=None,
            line_id="bl_00070",
            candidates=[
                {"settlement_id": "setl_020", "net_amount": 120000, "settlement_date": "2025-04-09"},
            ],
            credit_paise=120000,
            txn_date="2025-04-10",
        )
        text = explain_exception(inp)
        assert "UTR" in text
        assert "setl_020" in text
        assert "auto-close" in text.lower()

    def test_no_candidates(self):
        inp = ExplanationInput(
            reason_code="UTR_UNRESOLVED",
            confidence=0,
            settlement_id=None,
            line_id="bl_00071",
            candidates=[],
            credit_paise=99000,
            txn_date="2025-04-10",
        )
        text = explain_exception(inp)
        assert "UTR" in text
        assert "990" in text


class TestExplainDateOutOfWindow:
    def test_with_days(self):
        inp = ExplanationInput(
            reason_code="DATE_OUT_OF_WINDOW",
            confidence=50,
            settlement_id=None,
            line_id="bl_00080",
            candidates=[
                {"settlement_id": "setl_030", "distance_business_days": 5},
            ],
            credit_paise=800000,
            txn_date="2025-04-10",
        )
        text = explain_exception(inp)
        assert "setl_030" in text
        assert "5" in text
        assert "window" in text.lower()

    def test_without_days(self):
        inp = ExplanationInput(
            reason_code="DATE_OUT_OF_WINDOW",
            confidence=50,
            settlement_id=None,
            line_id="bl_00081",
            candidates=[
                {"settlement_id": "setl_031"},
            ],
            credit_paise=800000,
            txn_date="2025-04-10",
        )
        text = explain_exception(inp)
        assert "setl_031" in text
        assert "window" in text.lower()


class TestExplainBatchAmbiguous:
    def test_with_credit(self):
        inp = ExplanationInput(
            reason_code="BATCH_PARTITION_AMBIGUOUS",
            confidence=40,
            settlement_id=None,
            line_id="bl_00090",
            candidates=[
                {"settlement_id": "setl_040"},
                {"settlement_id": "setl_041"},
                {"settlement_id": "setl_042"},
            ],
            credit_paise=2000000,
            txn_date="2025-04-10",
        )
        text = explain_exception(inp)
        assert "batch" in text.lower()
        assert "20,000" in text

    def test_without_credit(self):
        inp = ExplanationInput(
            reason_code="BATCH_PARTITION_AMBIGUOUS",
            confidence=40,
            settlement_id=None,
            line_id="bl_00091",
            candidates=[{"settlement_id": "setl_040"}],
        )
        text = explain_exception(inp)
        assert "batch" in text.lower()


class TestExplainUnknownCode:
    def test_unknown_reason(self):
        inp = ExplanationInput(
            reason_code="SOME_NEW_REASON",
            confidence=50,
            settlement_id=None,
            line_id="bl_00100",
            candidates=[],
        )
        text = explain_exception(inp)
        assert "SOME_NEW_REASON" in text
        assert "review" in text.lower()


# ---------------------------------------------------------------------------
# Part 1 — Integration: API returns explanation field
# ---------------------------------------------------------------------------

class TestExplanationFieldInAPI:
    def test_exceptions_carry_explanation(self, client):
        """GET /api/exceptions returns an 'explanation' string on every row."""
        client.post("/api/run-reconciliation", params={"seed": 42})
        excs = client.get("/api/exceptions").json()
        assert len(excs) > 0
        for e in excs:
            assert "explanation" in e
            assert isinstance(e["explanation"], str)
            assert len(e["explanation"]) > 0

    def test_pending_approval_carry_explanation(self, client):
        """GET /api/exceptions/pending-approval also returns explanations."""
        client.post("/api/run-reconciliation", params={"seed": 42})
        # Resolve one to make it pending_approval
        excs = client.get("/api/exceptions", params={"status": "open"}).json()
        candidate = next(e for e in excs if e["settlement_id"] and e["line_id"])
        client.post(
            f"/api/exceptions/{candidate['exception_id']}/resolve",
            json={"maker_id": "alice", "action": "confirm"},
        )
        pend = client.get("/api/exceptions/pending-approval").json()
        assert len(pend) > 0
        for e in pend:
            assert "explanation" in e
            assert len(e["explanation"]) > 0

    def test_resolve_and_approve_return_explanation(self, client):
        """Single resolve/approve endpoints also return the explanation."""
        client.post("/api/run-reconciliation", params={"seed": 42})
        excs = client.get("/api/exceptions", params={"status": "open"}).json()
        candidate = next(e for e in excs if e["settlement_id"] and e["line_id"])
        eid = candidate["exception_id"]

        r = client.post(f"/api/exceptions/{eid}/resolve",
                        json={"maker_id": "alice", "action": "confirm"})
        assert "explanation" in r.json()
        assert len(r.json()["explanation"]) > 0

        r = client.post(f"/api/exceptions/{eid}/approve",
                        json={"checker_id": "bob", "decision": True})
        assert "explanation" in r.json()
        assert len(r.json()["explanation"]) > 0


# ---------------------------------------------------------------------------
# Part 2 — Constrained prompt (unit test)
# ---------------------------------------------------------------------------

class TestBuildExplainPrompt:
    def test_prompt_contains_only_given_facts(self):
        """The prompt must not introduce facts beyond the deterministic string + candidates."""
        deterministic = "This ₹5,000 credit doesn't match any settlement."
        prompt = build_explain_prompt(
            deterministic,
            reason_code="AMOUNT_MISMATCH",
            candidates=[{"settlement_id": "setl_001", "net_amount": 500000}],
            confidence=40,
        )
        # Must contain the input facts
        assert "AMOUNT_MISMATCH" in prompt
        assert "setl_001" in prompt
        assert deterministic in prompt
        assert "40" in prompt
        # Must instruct the model not to invent
        assert "Do NOT" in prompt or "do NOT" in prompt or "MUST" in prompt

    def test_prompt_without_candidates(self):
        deterministic = "No settlement found."
        prompt = build_explain_prompt(
            deterministic,
            reason_code="NO_CANDIDATE",
            candidates=[],
            confidence=None,
        )
        assert "NO_CANDIDATE" in prompt
        assert deterministic in prompt
        # No candidate details section
        assert "Candidate details" not in prompt

    def test_prompt_includes_candidate_details_when_present(self):
        deterministic = "Multiple matches."
        prompt = build_explain_prompt(
            deterministic,
            reason_code="MULTIPLE_CANDIDATES",
            candidates=[
                {"settlement_id": "setl_001", "net_amount": 100000, "settlement_date": "2025-04-10"},
                {"settlement_id": "setl_002"},
            ],
            confidence=60,
        )
        assert "setl_001" in prompt
        assert "setl_002" in prompt
        assert "1,000" in prompt  # 100000 paise = ₹1,000
        assert "2025-04-10" in prompt


# ---------------------------------------------------------------------------
# Part 2 — explain_with_llm (unit test with fake client)
# ---------------------------------------------------------------------------

class FakeGeminiClient:
    """Minimal fake that returns a canned response."""

    def __init__(self, response_text: str):
        self._response = response_text

    class _Models:
        def __init__(self, text):
            self._text = text

        def generate_content(self, **kwargs):
            result = MagicMock()
            result.text = self._text
            return result

    def __init__(self, response_text: str):
        self.models = self._Models(response_text)


class TestExplainWithLLM:
    def test_success_path(self):
        client = FakeGeminiClient('{"summary": "The credit of ₹5,000 has no matching settlement.", "notes": ""}')
        result = explain_with_llm(
            client,
            deterministic="This ₹5,000 credit doesn't match any settlement.",
            reason_code="AMOUNT_MISMATCH",
            candidates=[{"settlement_id": "setl_001"}],
            confidence=40,
            model="fake-model",
        )
        assert result["source"] == "llm"
        assert "5,000" in result["summary"]

    def test_parse_failure_returns_fallback(self):
        client = FakeGeminiClient("this is not json at all")
        result = explain_with_llm(
            client,
            deterministic="Fallback string.",
            reason_code="NO_CANDIDATE",
            candidates=[],
            confidence=None,
            model="fake-model",
        )
        assert result["source"] == "fallback"
        assert result["summary"] == "Fallback string."

    def test_api_exception_returns_fallback(self):
        class BrokenClient:
            class models:
                @staticmethod
                def generate_content(**kwargs):
                    raise ConnectionError("API down")

        result = explain_with_llm(
            BrokenClient(),
            deterministic="Safe fallback.",
            reason_code="NO_CANDIDATE",
            candidates=[],
            confidence=None,
            model="fake-model",
        )
        assert result["source"] == "fallback"
        assert result["summary"] == "Safe fallback."


# ---------------------------------------------------------------------------
# Part 2 — parse_explain_response (unit test)
# ---------------------------------------------------------------------------

class TestParseExplainResponse:
    def test_valid_json(self):
        r = _parse_explain_response('{"summary": "hello", "notes": "world"}')
        assert r == {"summary": "hello", "notes": "world"}

    def test_fenced_json(self):
        r = _parse_explain_response('```json\n{"summary": "hi", "notes": ""}\n```')
        assert r == {"summary": "hi", "notes": ""}

    def test_empty_text(self):
        assert _parse_explain_response("") is None

    def test_missing_summary(self):
        assert _parse_explain_response('{"notes": "only notes"}') is None

    def test_non_string_summary(self):
        assert _parse_explain_response('{"summary": 123, "notes": ""}') is None


# ---------------------------------------------------------------------------
# Part 2 — Endpoint tests (with fake LLM client)
# ---------------------------------------------------------------------------

def _make_fake_gen_factory(response_text: str):
    """Return a gen_factory callable that produces a fake Gemini client."""
    def _factory(api_key: str):
        return FakeGeminiClient(response_text)
    return _factory


class TestExplainEndpoint:
    def _setup_exception(self, client):
        """Run reconciliation and return the first open exception with line_id."""
        client.post("/api/run-reconciliation", params={"seed": 42})
        excs = client.get("/api/exceptions", params={"status": "open"}).json()
        return next(e for e in excs if e["line_id"])

    def test_explain_returns_deterministic_and_ai(self, client, monkeypatch):
        """POST /api/exceptions/{id}/explain returns both layers."""
        exc = self._setup_exception(client)

        fake_response = '{"summary": "AI rephrased version.", "notes": "extra context"}'
        from backend.app.services import llm_queue
        monkeypatch.setattr(
            llm_queue, "_default_gen_client",
            lambda key: FakeGeminiClient(fake_response),
        )

        r = client.post(f"/api/exceptions/{exc['exception_id']}/explain")
        assert r.status_code == 200
        body = r.json()
        assert body["exception_id"] == exc["exception_id"]
        assert len(body["explanation"]) > 0  # deterministic
        assert body["ai_summary"] == "AI rephrased version."
        assert body["source"] == "llm"

    def test_explain_caches_result(self, client, monkeypatch):
        """Second call returns cached result without re-calling the LLM."""
        exc = self._setup_exception(client)
        fake_response = '{"summary": "First call result.", "notes": ""}'
        call_count = {"n": 0}

        def counting_factory(key):
            call_count["n"] += 1
            return FakeGeminiClient(fake_response)

        from backend.app.services import llm_queue
        monkeypatch.setattr(llm_queue, "_default_gen_client", counting_factory)

        r1 = client.post(f"/api/exceptions/{exc['exception_id']}/explain")
        assert r1.status_code == 200
        first_call_count = call_count["n"]

        r2 = client.post(f"/api/exceptions/{exc['exception_id']}/explain")
        assert r2.status_code == 200
        assert r2.json()["ai_summary"] == "First call result."
        # No new LLM call — cache hit
        assert call_count["n"] == first_call_count

    def test_explain_fallback_on_failure(self, client, monkeypatch):
        """LLM failure returns the deterministic explanation with source=fallback."""
        exc = self._setup_exception(client)

        class FailFactory:
            def __init__(self, key):
                pass
            class models:
                @staticmethod
                def generate_content(**kwargs):
                    raise RuntimeError("boom")

        from backend.app.services import llm_queue
        monkeypatch.setattr(llm_queue, "_default_gen_client", lambda key: FailFactory(key))

        r = client.post(f"/api/exceptions/{exc['exception_id']}/explain")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "fallback"
        assert body["ai_summary"] == body["explanation"]  # falls back to deterministic

    def test_explain_404(self, client):
        r = client.post("/api/exceptions/99999/explain")
        assert r.status_code == 404

    def test_bulk_explain(self, client, monkeypatch):
        """POST /api/exceptions/explain with multiple ids."""
        client.post("/api/run-reconciliation", params={"seed": 42})
        excs = client.get("/api/exceptions", params={"status": "open"}).json()
        ids = [e["exception_id"] for e in excs[:3] if e["line_id"]]

        from backend.app.services import llm_queue
        monkeypatch.setattr(
            llm_queue, "_default_gen_client",
            lambda key: FakeGeminiClient('{"summary": "bulk result", "notes": ""}'),
        )

        r = client.post("/api/exceptions/explain", json={"ids": ids})
        assert r.status_code == 200
        results = r.json()
        assert len(results) == len(ids)
        for item in results:
            assert item["source"] == "llm"
            assert item["ai_summary"] == "bulk result"
