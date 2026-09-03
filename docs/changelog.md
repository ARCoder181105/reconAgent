# ReconAgent — Changelog

> Append-only. **Never edit or delete old entries.** Each entry records what changed, when, and why. Newest at top. Format: `YYYY-MM-DD — scope — description`.

---

- **2026-09-03 — docs** — Created the development docs set for ReconAgent under `docs/`. Moved the single master spec to `docs/master-design.md` (renamed from `master-document.md`) and added the supplementary build/domain/guardrail docs. Prefixed none; plain filenames per convention. Scope: this entire docs scaffold; no code yet.
- **2026-09-03 — docs (master design)** — Locked additions into `master-design.md`: Maker-Checker workflow (Decisions D6), event-sourced exception audit log (D2), async LLM offloading (D5), verified-rate metric, lightweight exception clustering, and a Future Scope section (§17). ChromaDB and Prometheus deliberately placed in Future Scope, not core. LLM structured output already present in the original design.
