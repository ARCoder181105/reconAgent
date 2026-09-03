# AGENTS.md — ReconAgent

Instructions for AI agents (opencode / Claude / any) working in this repo. Read this first, every session. It points to the real source of truth; do not re-derive context.

## Project

**ReconAgent** — Multi-Source Fuzzy Reconciliation Engine for the Razorpay Buildathon, Track 04 (AI Finance Controller). Matches a Razorpay-style settlement report against messy bank statement data across a 50+ record batch, reports measured accuracy, and surfaces an honest exception queue with a Maker-Checker workflow.

Product / domain context lives in `docs/`. Code lives in `backend/` and `frontend/` (not yet created).

## Source of Truth (READ THESE)

Ranked precedence — see `docs/sources-of-truth.md`. The master design wins all conflicts.

1. `docs/master-design.md` — ultimate source of truth (architecture, schema, pipeline, future scope)
2. `docs/decisions.md` — 8 locked decisions, must obey, no re-litigating
3. `docs/constraints.md` — hard limits
4. `docs/taxonomy.md` — canonical reason codes, confidence tiers, event types, metrics
5. `docs/scope.md` — in / out of scope (ChromaDB, Prometheus, cross-border, multi-currency, real-time OUT)
6. `docs/glossary.md` — locked term definitions

Supporting: `docs/architecture.md`, `docs/data-sources.md`, `docs/tech-stack.md`, `docs/flow.md`, `docs/conventions.md`.

State: `docs/tasks.md`, `docs/backlog.md`, `docs/changelog.md`, `docs/assumptions.md`, `docs/risks.md`.

## Environment

- Python **3.12.3** (pinned in `.python-version`).
- **Always use the venv**: `.venv` at repo root.
  - Activate: `source .venv/bin/activate`
  - Or run tools as `.venv/bin/python`, `.venv/bin/pytest`, etc.
  - Never install into system python.
- Dependencies in `requirements.txt`. Install/update: `.venv/bin/pip install -r requirements.txt`.
- Node/React (frontend) uses `frontend/package.json` (not yet created).

## Commands

```bash
# Backend
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest tests/            # once tests exist

# Run API
.venv/bin/uvicorn backend.app.main:app --reload
```

## Critical Guardrails (non-negotiable)

- **Hidden answer key**: `answer_key.json` is generated into `backend/data/` and is for scoring only. NEVER let it reach matcher scope. It is gitignored.
- **Event sourcing**: NEVER `UPDATE` exception status in place. Append to `exception_events`; status is a projection.
- **LLM = last resort**: Stage 5 only, async, Gemini structured output (fixed JSON schema), never sole authority.
- **Maker-Checker**: Maker proposes; only Checker closes books.
- **No real financial data**: synthetic only, INR/paise integers.

## Workflow rules for agents

- If you change engine/API/schema/behavior → update the relevant doc AND append to `docs/changelog.md`. Never edit old changelog entries.
- Don't invent reason codes or metric names — use `docs/taxonomy.md`.
- If two docs conflict → `docs/sources-of-truth.md` (master-design.md wins).
- If blocked or genuinely ambiguous → ask the human. Single-owner project.
- Do not add features outside `docs/scope.md`.

## Commit discipline (REQUIRED)

**Always commit after crossing a logical milestone** to keep history consistent and well-tracked. Do not batch unrelated work into one commit, and do not let changes accumulate uncommitted across the session.

- **When to commit**: at the close of each logical unit of work — a completed P0/P1/P2 task, a working new module, a fixed bug, a finished doc set, a verified passing test run. If in doubt, commit; an extra commit is cheaper than a lost or tangled one.
- **Commit message convention**: `conventional commits`, describing WHAT and WHY.
  - Format: `<type>: <imperative summary>`  (optionally `+ scope` if helpful)
  - Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `style`, `perf`
  - Examples:
    - `feat: add Stage 1 exact-UTR matcher`
    - `feat(api): add maker resolve + checker approve endpoints`
    - `fix: bound subset-sum search to date-window pools`
    - `docs: scaffold ReconAgent docs set under docs/`
    - `test: add precision/recall scoring against answer key`
    - `chore: scaffold venv, gitignore, AGENTS.md`
- **What to include**: stage only related files for the milestone. Never git add everything blindly (`git add -A`) when unrelated files changed.
- **Secrets**: never commit `.env`, API keys, or `backend/data/answer_key.json` (all gitignored).
- **Hooks/rules**: if a commit fails or a hook rejects it, fix and commit again — do not amend prior history casually, and never force-push.
- Before committing, review `git status` + `git diff` to ensure only intended files are staged.

## Skills

If `docs/tasks.md` moves into implementation, the `brainstorming` skill governs design changes (approve intent before coding). A `testing`/TDD skill should be introduced when backend code lands. See human before adding new skills.
