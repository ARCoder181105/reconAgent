# Iteration 11 — Docs Finalization + Demo Pack

> Phase P3 (polish). (**Status: done** — shipped with It11.)

## Goal

Finalize docs, add a README + demo script, and produce a repeatable demo flow — the polish that makes the submission easy to run and judge.

## Files

- `README.md` (repo root) — what it is, quickstart, demo path
- `docs/changelog.md` — reflect everything implemented across iterations
- `docs/tasks.md` — mark completed iterations done
- `docs/iterations/` — final pass to ensure each file matches what was actually built
- `scripts/demo.py` (or similar) — one-command: generate → run → score → print headline numbers
- `.env.example` — final (GEMINI_API_KEY documented)

## Key Notes

- README quickstart: venv, deps, generate, run, score, run API, run frontend.
- Include the pitch line: "verification capacity, not generation speed, is the bottleneck."
- State the 3x false-positive weighting as a deliberate choice (constraints.md / decisions.md D7).
- Explicitly note synthetic data = modeled, not real merchant data.
- Demo script should reproduce the honest numbers + exception list, not a cherry-picked match.

## Tests

- Demo script exits 0 and prints match/review/exception/verified rates + per-stage.
- README commands run from a clean clone (venv + pip install).

## Exit Criteria

- A judge (or fresh session) can generate/run/score in ~3 commands.
- Docs consistent with the shipped code.

## Commit

`docs: finalize docs and add demo pack`
