"""Iteration 08 — Stage 5: async LLM tie-break.

Genuinely unresolvable records after stages 1-4 get a LAST-RESORT, structured-
output LLM opinion. The result is ONE additional signal: it can rank a
candidate for human review but can never auto-confirm a financial match on its
own (see ``constraints.md``).

This module is deliberately decoupled from the SDK so it can be unit-tested with
a fake client. ``run_tiebreak`` expects a duck-typed Gemini client exposing
``client.chats.create(...)``; the SDK adapter
``make_gemini_client``/``run_tiebreak`` wiring is in ``llm_queue.py``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

# Signal provenance, so every AI-assisted decision keeps deterministic evidence.
SOURCE_LLM = "llm"
SOURCE_FALLBACK = "fallback"

_REASONING_MAX_CHARS = 400


@dataclass
class LLMDecision:
    """A parsed (or gracefully degraded) LLM tie-break opinion.

    ``match`` proposes WHICH candidate (if any) the line most likely belongs to.
    ``confidence`` is the LLM's claimed confidence (0-100), NOT the final match
    confidence — the caller decides how to use it (never auto-close).
    ``source`` records whether the decision came from the model or the
    deterministic fallback.
    """

    match: bool
    settlement_id: str | None
    confidence: int
    reasoning: str
    source: str = SOURCE_LLM

    def as_dict(self) -> dict:
        return {
            "match": self.match,
            "settlement_id": self.settlement_id,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "source": self.source,
        }


def build_tiebreak_prompt(line: dict, candidates: list[dict]) -> str:
    """Describe one bank line plus its remaining candidate settlements.

    ``candidates`` is a list of dicts with at least ``settlement_id``,
    ``net_amount`` and ``settlement_date``. Amounts are integer paise.
    """
    desc = line.get("description") or ""
    ref = line.get("ref_no") or ""
    credit_paise = line.get("credit_paise")
    txn = line.get("txn_date") or line.get("settlement_date") or line.get("value_date") or ""

    if not candidates:
        return (
            "Verify whether the following bank line corresponds to any Razorpay "
            "settlement. No candidate settlements remain; answer with match=false "
            "unless the amount is unambiguously attributable.\n"
            f"Bank line: ref={ref!r} desc={desc!r} credit_paise={credit_paise} txn={txn}"
        )

    cand_lines = []
    for i, c in enumerate(candidates, 1):
        cand_lines.append(
            f"  {i}. settlement_id={c.get('settlement_id')!r} "
            f"net_amount_paise={c.get('net_amount')} date={c.get('settlement_date')}"
        )
    cand_block = "\n".join(cand_lines)
    return (
        "You are the final tie-break stage of a settlement reconciliation "
        "pipeline. Stages 1-4 failed to uniquely match this bank line. Given the "
        "candidate settlements below, decide which one (if any) the line belongs "
        "to, or whether none fit. Be conservative: prefer no-match rather than a "
        "wrong match.\n"
        f"Bank line: ref={ref!r} desc={desc!r} credit_paise={credit_paise} txn={txn}\n"
        f"Candidate settlements:\n{cand_block}\n\n"
        "Respond with STRICT JSON only (no prose), shape: "
        '{"match": boolean, "settlement_id": "<id or null>", '
        '"confidence": int 0-100, "reasoning": "<short reason>"}'
    )


def parse_tiebreak_response(text: str) -> LLMDecision | None:
    """Parse a model response into a decision. Returns None if non-conforming.

    Tolerates a leading/trailing markdown fence and stray whitespace, but
    rejects chatty/prose responses — the caller falls back on None.
    """
    if not text:
        return None
    cleaned = text.strip()
    # Strip a ```json ... ``` fence if any.
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None

    match = data.get("match")
    if not isinstance(match, bool):
        return None
    sid = data.get("settlement_id")
    if sid is not None and not isinstance(sid, str):
        return None
    confidence = data.get("confidence")
    if not isinstance(confidence, int) or isinstance(confidence, bool):
        return None
    confidence = max(0, min(100, confidence))
    reasoning = data.get("reasoning")
    if not isinstance(reasoning, str):
        reasoning = ""
    reasoning = reasoning[:_REASONING_MAX_CHARS]
    return LLMDecision(
        match=match, settlement_id=sid, confidence=confidence, reasoning=reasoning
    )


def fallback_decision() -> LLMDecision:
    """Deterministic degradation signal when the LLM is unavailable/malformed.

    Reflects the most conservative stance: cannot confirm a match, so the record
    stays in review. Marked ``source=fallback`` so evidence is preserved.
    """
    return LLMDecision(
        match=False,
        settlement_id=None,
        confidence=0,
        reasoning="LLM unavailable/malformed; falling back to deterministic signal (stays in review).",
        source=SOURCE_FALLBACK,
    )


def run_tiebreak(client, line: dict, candidates: list[dict], model: str) -> LLMDecision:
    """Invoke Gemini with structured output, then strictly parse.

    ``client`` is a duck-typed object with ``client.chats.create``.
    Any API exception, timeout, or parse failure degrades to ``fallback_decision``
    so the pipeline never crashes or silently breaks.
    """
    prompt = build_tiebreak_prompt(line, candidates)
    try:
        chat = client.chats.create(
            model=model,
            config={
                "response_mime_type": "application/json",
                "response_schema": _response_schema(),
            },
        )
        resp = chat.send_message(prompt)
        text = resp.text if hasattr(resp, "text") else str(resp)
        decision = parse_tiebreak_response(text)
        return decision if decision is not None else fallback_decision()
    except Exception:
        return fallback_decision()


def _response_schema():
    """JSON schema for the structured LLM output (strict, boolean/int/string)."""
    import google.genai as genai

    T = genai.types.Type
    return genai.types.Schema(
        type=T.OBJECT,
        properties={
            "match": genai.types.Schema(type=T.BOOLEAN, description="true if this line belongs to a candidate"),
            "settlement_id": genai.types.Schema(type=T.STRING, description="matched settlement id, or null"),
            "confidence": genai.types.Schema(type=T.INTEGER, description="0-100 confidence"),
            "reasoning": genai.types.Schema(type=T.STRING, description="short reason"),
        },
        required=["match", "settlement_id", "confidence", "reasoning"],
    )
