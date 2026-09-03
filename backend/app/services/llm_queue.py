"""Iteration 08 — in-process async background queue for LLM tie-breaks.

The reconcile endpoint returns deterministic results immediately; a background
daemon thread drains queued stage-5 candidates and persists each LLM opinion as
an append-only ``AI_TIEBREAK_SUGGESTED`` event on the owning exception.

Governance rules (non-negotiable):
- The LLM can ONLY add signal. It can bump an exception's confidence into the
  review band / rank a candidate, but it can never close an exception (status is
  only ever changed by a Checker) and never fabricate a match with no candidate.
- On LLM failure a deterministic fallback opinion is persisted instead.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.app import models
from backend.app.db import SessionLocal
from backend.app.matcher import llm_tiebreak
from backend.app.services.constants import EVENT_AI_TIEBREAK_SUGGESTED

# LLM output is used to rank for review; it can lift confidence into the
# review band but never into auto-close territory.
REVIEW_BAND_CEILING = 84
CONFIDENCE_IF_CONFIDENT = 70  # reviewer-facing signal when LLM proposes a match


@dataclass
class TiebreakTask:
    """One unresolved record the LLM may disambiguate for human review."""

    exception_id: int
    line: dict
    candidates: list[dict] = field(default_factory=list)
    settlement_id: str | None = None
    reason_code: str | None = None


class TiebreakQueue:
    """Thread-safe in-process queue drained by a single daemon worker.

    ``run_fn`` / ``gen_factory`` are injectable for tests; production uses the
    google-genai client. The worker uses its own DB session so it does not
    contend with the request session.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        run_fn=None,
        gen_factory=None,
        session_factory=None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._run_fn = run_fn or _default_run
        self._gen_factory = gen_factory or _default_gen_client
        self._session_factory = session_factory or SessionLocal
        self._tasks: list[TiebreakTask] = []
        self._lock = threading.Lock()
        self._worker: threading.Thread | None = None
        self._processed = 0
        self._failed = 0

    # --- producer side ---

    def enqueue(self, task: TiebreakTask) -> None:
        with self._lock:
            self._tasks.append(task)

    def pending(self) -> int:
        with self._lock:
            return len(self._tasks)

    def processed(self) -> int:
        with self._lock:
            return self._processed

    def failed(self) -> int:
        with self._lock:
            return self._failed

    def start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        self._worker = threading.Thread(target=self._drain, daemon=True)
        self._worker.start()

    # --- worker side ---

    def _drain(self) -> None:
        client = self._gen_factory(self.api_key)
        while True:
            with self._lock:
                if not self._tasks:
                    break
                task = self._tasks.pop(0)
            try:
                decision = self._run_fn(client, task, self.model)
                self._persist(task, decision)
                with self._lock:
                    self._processed += 1
            except Exception:
                with self._lock:
                    self._failed += 1
            finally:
                if not self._tasks:
                    break

    def _persist(self, task: TiebreakTask, decision: llm_tiebreak.LLMDecision) -> None:
        now = datetime.now(timezone.utc)
        db = self._session_factory()
        try:
            exc = db.get(models.Exception, task.exception_id)
            if exc is None:
                return
            # Preserve the proposed candidate ranking, but keep governance intact.
            if decision.match and decision.settlement_id:
                proposed = next(
                    (c for c in task.candidates if c.get("settlement_id") == decision.settlement_id),
                    None,
                )
                if proposed is not None and exc.confidence is not None:
                    # Signal only; never cross into auto-close (>=85) — stays open.
                    exc.confidence = min(
                        max(exc.confidence, CONFIDENCE_IF_CONFIDENT), REVIEW_BAND_CEILING
                    )
                if exc.candidates_json:
                    merged = _merge_candidates(exc.candidates_json, task.candidates, decision)
                    exc.candidates_json = _dump_json(merged)

            db.add(
                models.ExceptionEvent(
                    exception_id=exc.exception_id,
                    event_type=EVENT_AI_TIEBREAK_SUGGESTED,
                    resolution_data=_dump_json(decision.as_dict()),
                    reason_text=f"LLM tie-break ({decision.source}): {decision.reasoning}",
                    timestamp=now,
                )
            )
            db.commit()
        finally:
            db.close()


def _merge_candidates(candidates_json: str, task_candidates: list[dict], decision) -> str:
    base = []
    try:
        from json import loads

        base = loads(candidates_json or "[]")
    except Exception:
        base = []
    keyed = {str(c.get("settlement_id")): c for c in base if c.get("settlement_id")}
    if decision.match and decision.settlement_id:
        keyed[str(decision.settlement_id)] = {"settlement_id": decision.settlement_id, "ai": True}
        for c in task_candidates:
            keyed.setdefault(str(c.get("settlement_id")), {"settlement_id": c.get("settlement_id")})
    return _dump_json(list(keyed.values()))


def _dump_json(obj) -> str:
    import json

    return json.dumps(obj, default=str)


def _default_gen_client(api_key: str):
    from google.genai import Client

    if api_key:
        return Client(api_key=api_key)
    return Client()


def _default_run(client, task: TiebreakTask, model: str) -> llm_tiebreak.LLMDecision:
    return llm_tiebreak.run_tiebreak(client, task.line, task.candidates, model)
