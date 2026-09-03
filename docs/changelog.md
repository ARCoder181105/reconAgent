# ReconAgent — Changelog

> Append-only. **Never edit or delete old entries.** Each entry records what changed, when, and why. Newest at top. Format: `YYYY-MM-DD — scope — description`.

---

- **2026-09-03 — feat(matcher) — It8** — Added async LLM tie-break (Stage 5) with graceful fallback. New `backend/app/matcher/llm_tiebreak.py` (strict JSON schema, parse, fallback, `run_tiebreak`) and `backend/app/services/llm_queue.py` (thread-safe in-process `TiebreakQueue`, daemon-thread drain, injectable `run_fn`/`gen_factory`/`session_factory`). Wired the queue into `reconcile_service.run_reconciliation` (+ `enqueue_tiebreaks`) and exposed `GET /api/ai-tiebreaks` (pending/processed/failed). Consolidated `AI_TIEBREAK_SUGGESTED` into `services/constants.py`. Governance: the LLM only adds review signal, bumps confidence up to 84, and never auto-closes. Added `backend/tests/test_llm_tiebreak.py` (15 tests). Deterministic eval unchanged: precision 1.0, recall 0.9167, F1 0.9565, penalized 0.9167. Full suite 62 passing.
- **2026-09-03 — docs** — Created the development docs set for ReconAgent under `docs/`. Moved the single master spec to `docs/master-design.md` (renamed from `master-document.md`) and added the supplementary build/domain/guardrail docs. Prefixed none; plain filenames per convention. Scope: this entire docs scaffold; no code yet.
- **2026-09-03 — docs (master design)** — Locked additions into `master-design.md`: Maker-Checker workflow (Decisions D6), event-sourced exception audit log (D2), async LLM offloading (D5), verified-rate metric, lightweight exception clustering, and a Future Scope section (§17). ChromaDB and Prometheus deliberately placed in Future Scope, not core. LLM structured output already present in the original design.
