"""Deterministic plain-language explanations for the exception queue.

Part 1 of the two-layer explanation system.  Each exception carries a
one-line summary generated from data already in the DB — no LLM, no API
cost, no latency.  The templates are plain f-strings keyed by reason code.

Part 2 (optional, on-demand) lives at the bottom of this file and adds an
LLM rephrase layer that rewrites the deterministic string for readability.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Part 1 — Deterministic explanation
# ---------------------------------------------------------------------------

# Amounts in the DB are paise (integers).  This formatter is intentionally
# lightweight — no locale dependency, just "₹X,XXX".
_RUPEE符号 = "₹"


def _fmt_paise(v: int | float | None) -> str:
    """Format paise integer as a rupee string, e.g. 12345 -> '₹123'."""
    if v is None:
        return "unknown amount"
    rupees = int(round(float(v) / 100))
    return f"{_RUPEE符号}{rupees:,}"


def _fmt_date(d: str | None) -> str:
    if not d:
        return "unknown date"
    return d


def _top_candidate_ids(candidates: list[dict], limit: int = 3) -> str:
    ids = [c.get("settlement_id", "?") for c in candidates[:limit]]
    return ", ".join(ids)


@dataclass
class ExplanationInput:
    """All the data needed to build a deterministic explanation."""

    reason_code: str
    confidence: int | None
    settlement_id: str | None
    line_id: str | None
    candidates: list[dict]
    credit_paise: int | None = None  # bank line credit amount in paise
    txn_date: str | None = None  # bank line transaction date


def explain_exception(inp: ExplanationInput) -> str:
    """Return a one-line plain-English explanation for an exception.

    Templates are keyed by reason code.  Missing data produces graceful
    fallbacks — the string is always a complete sentence.
    """
    rc = inp.reason_code
    credit = inp.credit_paise
    date = inp.txn_date
    cands = inp.candidates
    sid = inp.settlement_id

    if rc == "NO_CANDIDATE":
        return _explain_no_candidate(credit, date, cands, sid)
    if rc == "MULTIPLE_CANDIDATES":
        return _explain_multiple(cands, credit, date)
    if rc == "AMOUNT_MISMATCH":
        return _explain_amount_mismatch(cands, credit, date)
    if rc == "UTR_UNRESOLVED":
        return _explain_utr_unresolved(cands, credit, date)
    if rc == "DATE_OUT_OF_WINDOW":
        return _explain_date_out_of_window(cands, credit, date)
    if rc == "BATCH_PARTITION_AMBIGUOUS":
        return _explain_batch_ambiguous(cands, credit, date)

    # Fallback for any unknown reason code.
    return f"Exception with reason code {rc} — review required."


# --- Templates ---


def _explain_no_candidate(credit, date, cands, sid):
    # Two sub-cases: bank debit (no credit) vs credit with no match,
    # vs settlement not credited in bank statement.
    if sid and credit is None:
        # Settlement-side NO_CANDIDATE: settlement exists but no bank line matched it.
        return f"Settlement {sid} was not found in the bank statement."
    if credit is None:
        return "Bank-side debit with no Razorpay settlement."
    amt = _fmt_paise(credit)
    dt = _fmt_date(date)
    return f"No settlement was found within the search window for this {amt} credit on {dt}."


def _explain_multiple(cands, credit, date):
    n = len(cands)
    ids = _top_candidate_ids(cands)
    if credit is not None:
        amt = _fmt_paise(credit)
        dt = _fmt_date(date)
        suffix = f" from {dt}" if date else ""
        return (
            f"This {amt} credit{suffix} matches {n} settlements equally well "
            f"({ids}) — needs a human call."
        )
    return (
        f"Multiple settlements ({ids}) are equally likely candidates — "
        f"needs a human call."
    )


def _explain_amount_mismatch(cands, credit, date):
    if not cands:
        if credit is not None:
            return f"This {_fmt_paise(credit)} bank credit on {_fmt_date(date)} doesn't match any settlement."
        return "No candidate settlements found; amount mismatch."
    top = cands[0]
    cand_sid = top.get("settlement_id", "?")
    cand_amt = top.get("net_amount")
    if credit is not None and cand_amt is not None:
        delta_paise = abs(int(credit) - int(cand_amt))
        return (
            f"This {_fmt_paise(credit)} bank credit doesn't exactly match any settlement. "
            f"Closest: {cand_sid} ({_fmt_paise(cand_amt)}) — a {_fmt_paise(delta_paise)} gap."
        )
    return (
        f"This {_fmt_paise(credit)} bank credit doesn't exactly match any settlement. "
        f"Closest candidate: {cand_sid}."
    )


def _explain_utr_unresolved(cands, credit, date):
    if not cands:
        if credit is not None:
            return (
                f"No UTR could be matched from the bank description for this "
                f"{_fmt_paise(credit)} credit on {_fmt_date(date)}."
            )
        return "No UTR could be matched from the bank description."
    top = cands[0]
    cand_sid = top.get("settlement_id", "?")
    if credit is not None:
        return (
            f"No UTR could be matched from the bank description. "
            f"Closest amount+date candidate is {cand_sid}, but not confident "
            f"enough to auto-close."
        )
    return (
        f"No UTR could be matched. Closest candidate is {cand_sid}, "
        f"but not confident enough to auto-close."
    )


def _explain_date_out_of_window(cands, credit, date):
    if not cands:
        return (
            f"Settlement amount matches but the date is outside the matching "
            f"window for this {_fmt_paise(credit)} credit on {_fmt_date(date)}."
        )
    top = cands[0]
    cand_sid = top.get("settlement_id", "?")
    days = top.get("distance_business_days")
    if days is not None:
        return (
            f"{cand_sid} matches on amount but settled {days} business days "
            f"outside the matching window."
        )
    return f"{cand_sid} matches on amount but the settlement date is outside the matching window."


def _explain_batch_ambiguous(cands, credit, date):
    n = len(cands)
    if credit is not None:
        return (
            f"This {_fmt_paise(credit)} credit could be a batch settlement "
            f"of {n} different combinations of unmatched settlements — "
            f"no single valid split was found."
        )
    return (
        f"This bank credit could be a batch settlement of {n} different "
        f"combinations — no single valid split was found."
    )


# ---------------------------------------------------------------------------
# Part 2 — On-demand AI rephrase layer (called only on human click)
# ---------------------------------------------------------------------------

SOURCE_LLM = "llm"
_SOURCE_FALLBACK = "fallback"


def build_explain_prompt(deterministic: str, reason_code: str, candidates: list[dict], confidence: int | None) -> str:
    """Build a constrained prompt for the LLM rephrase.

    The prompt explicitly tells the model to rephrase ONLY the facts given —
    no numbers, dates, IDs, or claims beyond what's in the deterministic
    string and the candidate list.
    """
    cand_summary = ""
    if candidates:
        ids = [c.get("settlement_id", "?") for c in candidates]
        cand_summary = f"\nCandidate settlement IDs: {', '.join(ids)}."
        # Include amounts/dates only if present, so the LLM doesn't hallucinate them.
        details = []
        for c in candidates:
            parts = [c.get("settlement_id", "?")]
            if c.get("net_amount") is not None:
                parts.append(f"amount={_fmt_paise(c['net_amount'])}")
            if c.get("settlement_date"):
                parts.append(f"date={c['settlement_date']}")
            if len(parts) > 1:
                details.append(" (" + ", ".join(parts[1:]) + ")")
        if details:
            cand_summary += "\nCandidate details:" + "".join(details)

    conf_str = f"\nConfidence: {confidence}." if confidence is not None else ""

    return (
        "You are a readability assistant for a financial reconciliation system. "
        "Rephrase the following one-line explanation in clearer, more natural "
        "language. You MUST use ONLY the facts provided below. Do NOT invent "
        "any number, date, settlement ID, or claim that is not explicitly "
        "present in the input. Keep it to 1-2 sentences.\n"
        f"\nReason code: {reason_code}"
        f"{conf_str}"
        f"{cand_summary}"
        f"\nDeterministic explanation: {deterministic}"
        "\n\nRespond with STRICT JSON: {\"summary\": \"<rephrased>\", \"notes\": \"<optional context>\"}"
    )


def _parse_explain_response(text: str) -> dict | None:
    """Parse the LLM's structured JSON response. Returns None on failure."""
    if not text:
        return None
    cleaned = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        return None
    notes = data.get("notes", "")
    if not isinstance(notes, str):
        notes = ""
    return {"summary": summary.strip(), "notes": notes.strip()}


def explain_with_llm(client, deterministic: str, reason_code: str,
                     candidates: list[dict], confidence: int | None,
                     model: str) -> dict:
    """Call Gemini to rephrase the deterministic explanation.

    Returns {"summary": str, "notes": str, "source": "llm"|"fallback"}.
    On any failure, returns the deterministic string as the summary with
    source="fallback" — same graceful-degradation pattern as llm_tiebreak.
    """
    prompt = build_explain_prompt(deterministic, reason_code, candidates, confidence)
    try:
        chat = client.chats.create(
            model=model,
            config={
                "response_mime_type": "application/json",
                "response_schema": _explain_response_schema(),
            },
        )
        resp = chat.send_message(prompt)
        text = resp.text if hasattr(resp, "text") else str(resp)
        parsed = _parse_explain_response(text)
        if parsed is not None:
            return {"summary": parsed["summary"], "notes": parsed["notes"], "source": SOURCE_LLM}
        return _fallback(deterministic)
    except Exception:
        return _fallback(deterministic)


def _fallback(deterministic: str) -> dict:
    return {"summary": deterministic, "notes": "", "source": _SOURCE_FALLBACK}


def _explain_response_schema():
    """JSON schema for the structured LLM output."""
    import google.genai as genai

    T = genai.types.Type
    return genai.types.Schema(
        type=T.OBJECT,
        properties={
            "summary": genai.types.Schema(type=T.STRING, description="rephrased explanation"),
            "notes": genai.types.Schema(type=T.STRING, description="optional additional context"),
        },
        required=["summary", "notes"],
    )
