# Code.ved - View/Edit/Debug

A web application for creating, versioning, and running Python scripts with LLM's help.

## Read more

| File | Contents |
| --- | --- |
| [`concept.md`](concept.md) | Full architecture spec - components, data model, execution engine, auth |
| [`phase1-2.md`](phase1-2.md) | Two-phase delivery plan with scope boundaries and hour estimates |
| [`phase1steps.md`](phase1steps.md) | Step-by-step Phase 1 implementation plan (12 steps) |

## Current status

**Phase 1 - in progress**

- [x] Step 1 - Scaffolding & tooling (frontend/backend bootstrapped, scripts_repo initialized)
- [x] Step 2 - Database schema (SQLModel)
- [x] Step 3 - Git store (GitPython)
- [x] Step 4 - Auth (session cookie, 2 hardcoded users)
- [x] Step 5 - Script management REST API
- [x] Step 6 - Docker execution sandbox
- [x] Step 7 - LLM proxy (OpenRouter)
- [x] Step 8 - Frontend foundation (routing, auth context)
- [x] Step 9 - Script catalog UI
- [x] Step 10 - Script editor UI (Monaco - ~Pyright worker~)
- [x] Step 11 - Static file serving (production)
- [x] Step 12 - Testing & stabilization (67 tests)

## Prerequisites

| Tool | Version | Purpose |
| --- | --- | --- |
| [Docker](https://docs.docker.com/get-docker/) | 24+ | Script execution sandbox |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Python package management (backend) |
| [Node.js](https://nodejs.org/) | 24 | Frontend build tooling |
| npm | bundled with Node | Frontend package management |
| Git | any recent | scripts_repo version store |
| OpenRouter API key | - | LLM features - set in `backend/.env` (see [`sample.env`](backend/sample.env)) |

Python 3.13 is managed automatically by `uv`; no separate install needed.

Run `cd backend && uv run python check_llm.py` to check LLM connectivity.

## Dev setup (once Phase 1 is complete)

```bash
# Terminal 1 - backend
cd backend
uv run uvicorn app.main:app --reload

# Terminal 2 - frontend
cd frontend
npm run dev
```

Open `http://localhost:5173`. Login as `ed1` / `1editor` (editor) or `mo1` / `2viewer` (viewer).

## Production setup

```bash
# Build the frontend once (or after any frontend changes)
cd frontend
npm run build

# Run the backend — it detects frontend/dist/ and serves it at /
cd ../backend
uv run uvicorn app.main:app
```

Open `http://localhost:8000`. No Vite process needed.

## Running tests

```bash
cd backend
uv run pytest          # run all 67 tests
uv run pytest -v       # verbose (show each test name)
uv run pytest tests/test_auth.py   # single file
```

Tests use an isolated in-memory SQLite database and a temporary git repo — no running services required.
