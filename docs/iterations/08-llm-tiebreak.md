# Iteration 08 — Async LLM Tie-break

> Phase P2. (Depends on 07.)

## Goal

Stage 5 as an asynchronous, structured-output LLM tie-break for whatever stages 1–4 could not close — with graceful degradation so the pipeline never breaks on API failure.

## Files

- `backend/app/matcher/llm_tiebreak.py` — Gemini call, structured output, fallback
- `backend/app/services/llm_queue.py` — async background queue (in-process; no broker)
- `backend/config.py` — add `GEMINI_API_KEY` (from `.env`, gitignored)

## Behavior

- Only handles records unresolved after stages 1–4. Last resort, never sole authority.
- Gemini structured output → strict JSON schema: `{match: bool, confidence: int, reasoning: string}`. Rejects chatty/non-conforming responses.
- Result is ONE additional signal. It can move a borderline case into review, but cannot auto-confirm a financial match on its own.
- Every LLM-assisted decision retains deterministic evidence alongside the LLM reasoning.
- **Throughput protection**: endpoint returns deterministic results immediately; LLM work runs in background; dashboard shows "Processing AI tie-breaks…" (09).

## Fallback (non-negotiable, from `constraints.md`)

On rate-limit/timeout/parse-error: fall back to the best deterministic signal (e.g. Stage 4 result) with a lower-confidence label. Pipeline stays alive; nothing silently breaks.

## Tests

- Mocked LLM returns schema-conformant JSON → parsed into decision.
- Mocked LLM returns malformed/chatty text → rejected gracefully, fallback used.
- Mocked API exception → fallback path, no crash.
- Async queue drains and results persist to `Match`/`Exception` events.

## Exit Criteria

- Stage 5 wired into the reconcile flow as the async tail.
- Verified resilient to LLM failure.

## Commit

`feat(matcher): add async LLM tie-break with graceful fallback`
