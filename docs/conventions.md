# ReconAgent — Conventions

> Naming, file structure, code style. Locked for consistency. Source: `master-design.md` §13.

## Language / Formatting

- Python 3.11+. Use `black`-style formatting, `isort` import ordering.
- Type hints on all public function signatures.
- Docstrings on modules and public functions.
- No comments that restate the code; add a comment only to explain *why* (non-obvious rationale).
- React: functional components + hooks, no class components.

## Naming

| Kind | Convention | Example |
|---|---|---|
| Python files | snake_case | `stage1_exact.py` |
| Python functions/vars | snake_case | `match_utr(record)` |
| Python classes | PascalCase | `MatchingPipeline` |
| JS/React files & components | PascalCase | `ExceptionQueue.jsx` |
| DB tables | snake_case | `exception_events` |
| Reason codes | UPPER_SNAKE | `NO_CANDIDATE` |
| Constants | UPPER_SNAKE | `CONFIDENCE_AUTO_HIGH = 95` |
| API routes | kebab/lower path | `/api/exceptions/{id}/approve` |

## Project Structure

Reference layout in `master-design.md` §13. Key rules:

- `backend/app/` — FastAPI app (models, schemas, db, main)
- `backend/app/data_generator/` — generator + answer key
- `backend/app/matcher/` — pipeline stages + normalize
- `backend/scoring/` — offline scoring (never imported by engine)
- `backend/data/` — generated CSVs + `answer_key.json` (never leak to matcher)
- `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/api/`

## Database Conventions

- Amounts stored as **integer paise**, never float (except the noisy bank `balance` column, which is REAL and unused for matching).
- Dates normalized to ISO 8601 (YYYY-MM-DD) at Stage 0.
- Foreign keys explicit; `exceptions.status` is a denormalized projection, not the system of record.

## Git / Commit Style (if version-controlled)

- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`.
- Never commit secrets or the hidden answer key content in a way that leaks to the matcher path.
- Small, focused commits.

## Docs

- This folder is the living spec. When changing behavior, update the relevant doc + `changelog.md`.
- Never edit old `changelog.md` entries — append only.
- Prefer the canonical doc over ad hoc notes; if a two-doc conflict appears, `sources-of-truth.md` resolves it.
