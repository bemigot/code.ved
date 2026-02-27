# Phase 1 Implementation Plan

## Context

Starting from a documentation-only repo (concept.md + phase1-2.md). No source code exists.
Goal: Build a fully functional LLM-powered Python scripting environment for Phase 1 scope:
single Docker interpreter, browser Pyright, 2 hardcoded users, REST-only, no WebSockets.

**Decided:**
- Monorepo: `frontend/` + `backend/` under repo root
- Auth: session cookie (Starlette `SessionMiddleware`, signed cookie)
- Dev: two terminals — `npm run dev` (Vite, port 5173) proxying `/api` → uvicorn (port 8000)
- DB layer: SQLModel (SQLAlchemy + Pydantic in one model class)

---

## Target Directory Layout

```
code.ved/
├── frontend/                        # React 19 + Vite + TypeScript
│   ├── src/
│   │   ├── api/                     # typed fetch wrappers
│   │   ├── services/
│   │   │   └── LanguageService.ts   # abstraction hook (Phase 1: Pyright Worker)
│   │   ├── components/
│   │   │   ├── ScriptCatalog/
│   │   │   └── ScriptEditor/
│   │   └── App.tsx
│   ├── public/
│   ├── vite.config.ts               # proxy /api → localhost:8000
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, SessionMiddleware, static serving
│   │   ├── auth.py                  # hardcoded users, session helpers, dependency
│   │   ├── db.py                    # SQLModel engine + session factory
│   │   ├── models.py                # all SQLModel table models
│   │   ├── git_store.py             # Git operations via GitPython
│   │   ├── routes/
│   │   │   ├── scripts.py           # CRUD + versioning endpoints
│   │   │   ├── execution.py         # run single / run all
│   │   │   └── llm.py               # LLM proxy + guardrails
│   │   └── executor/
│   │       ├── docker_runner.py     # single-script Docker execution
│   │       └── grouper.py           # ordering_number grouping + concurrency
│   ├── scripts_repo/                # Git repo managed by git_store.py (gitignored)
│   ├── data.db                      # SQLite file (gitignored)
│   ├── pyproject.toml               # uv-managed dependencies
│   └── Dockerfile.runner            # CPython 3.14 slim image for script execution
└── .gitignore                       # add: backend/scripts_repo/, backend/data.db, node_modules, dist
```

---

## Implementation Steps

### Step 1 — Scaffolding & Tooling

1. Update `.gitignore` with `node_modules/`, `dist/`, `backend/scripts_repo/`, `backend/data.db`, `__pycache__/`, `.venv/`
2. Bootstrap frontend: `npm create vite@latest frontend -- --template react-ts`
   - Add deps: `@monaco-editor/react`, `monaco-editor`, `react-router-dom`, `monaco-languageclient`, `vscode-languageclient`, `pyright`
3. Bootstrap backend: `uv init backend --python 3.12`
   - Add deps: `fastapi`, `uvicorn[standard]`, `sqlmodel`, `gitpython`, `openai`, `docker`, `itsdangerous`
4. Initialize `scripts_repo` as a bare Git repo with `prod` and `ed1` branches
5. Configure Vite proxy: `/api` → `http://localhost:8000` in `vite.config.ts`

---

### Step 2 — Database Schema (SQLModel)

File: `backend/app/models.py`

```
Script
  id: int PK
  ordering_number: float  (e.g. 3.01)
  is_deleted: bool

ScriptVersion
  id: int PK
  script_id: FK Script
  major: int
  minor: int              # auto-incremented by backend on save
  git_commit_hash: str
  committer: str          # "ed1" etc.
  created_at: datetime    # 0.01s precision
  parent_script_id: int | None  # set on fork
  parent_version_id: int | None

Execution
  id: int PK
  script_version_id: FK ScriptVersion
  started_at / finished_at: datetime
  exit_code: int
  stdout / stderr: str
  interpreter: str        # "cpython-3.14"

LLMInteraction
  id: int PK
  script_version_id: FK ScriptVersion | None
  prompt: str
  response: str
  model_id: str
  input_tokens / output_tokens: int
  cost_usd: float
  latency_ms: int
  created_at: datetime
```

File: `backend/app/db.py` — SQLModel engine + `get_session` dependency + `create_db_and_tables()` on startup.

---

### Step 3 — Git Store

File: `backend/app/git_store.py`

Operations (using `gitpython`):
- `init_repo()` — called on startup, creates `scripts_repo/` + branches `prod` and `ed1` if absent
- `commit_script(branch, script_id, content, message) -> str` — writes file to worktree, commits, returns hash
- `get_script_content(branch, script_id) -> str`
- `list_scripts_on_branch(branch) -> list[str]` — list of script file names
- `merge_to_prod(script_id)` — fast-forward or merge `ed1` → `prod` for one script file

Scripts stored as `{script_id}.py` files in the repo root.

---

### Step 4 — Auth (Session Cookie)

File: `backend/app/auth.py`

```python
USERS = {
    "ed1": {"password": "1editor", "roles": ["viewer", "editor"]},
    "mo1": {"password": "2viewer", "roles": ["viewer"]},
}
```

- `SessionMiddleware(app, secret_key=..., session_cookie="ved_session")`
- `POST /api/auth/login` — validates credentials, sets `request.session["user"]`
- `POST /api/auth/logout` — clears session
- `GET /api/auth/me` — returns current user + roles
- FastAPI dependency `require_viewer` / `require_editor` — reads session, raises 401/403

---

### Step 5 — Script Management Routes

File: `backend/app/routes/scripts.py`

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/api/scripts` | GET | viewer | List all (ordering_number, name from docstring line 1, latest version, last run status) |
| `/api/scripts/{id}` | GET | viewer | Script content + full metadata |
| `/api/scripts` | POST | editor | Create new — assigns next integer Major ordering_number, initial version `0.1`, commits to `ed1` |
| `/api/scripts/{id}` | PUT | editor | Save — auto-increment Minor, commit to `ed1` |
| `/api/scripts/{id}/fork` | POST | editor | Clone content to new Script, record parent in ScriptVersion |
| `/api/scripts/{id}/bump-major` | POST | editor | Increment Major by 1, reset Minor to 0 (next save → X.1) |
| `/api/scripts/{id}/merge` | POST | editor | Merge `ed1` → `prod` for this script |
| `/api/scripts/{id}/versions` | GET | viewer | List version history |

Ordering number assignment: `max(floor(ordering_number) for all scripts) + 1`.
`descriptive_name`: parse first non-empty line of docstring; fall back to `"Untitled"`.

---

### Step 6 — Docker Execution Sandbox

File: `backend/Dockerfile.runner`
```dockerfile
FROM python:3.14-slim
WORKDIR /runner
ENTRYPOINT ["python"]
```

File: `backend/app/executor/docker_runner.py`
- `run_script(script_id, version_id, content, test_data) -> ExecutionResult`
  - Write `content` to temp file
  - Write `test_data` to second temp file (the arg)
  - `docker run --rm --network none --memory 256m --cpus 0.5 -v tmpdir:/runner python:3.14-slim python /runner/script.py /runner/input`
  - Capture stdout/stderr, timeout 30s
  - Persist `Execution` row in SQLite

File: `backend/app/executor/grouper.py`
- `group_scripts(scripts) -> list[list[Script]]` — group by `floor(ordering_number)`, sort groups by key
- `POST /api/execute/all`:
  ```
  for group in groups:
      await asyncio.gather(*[run_script(s) for s in group])
  ```

File: `backend/app/routes/execution.py`
- `POST /api/execute/{id}` — run single script (uses content from `prod` branch)
- `POST /api/execute/all` — run all scripts per grouper logic
- `GET /api/execute/{id}/last` — last execution result

---

### Step 7 — LLM Proxy

File: `backend/app/routes/llm.py`

```python
client = openai.AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)
```

- `POST /api/llm/complete` — body: `{script_id, script_version_id, prompt, context_code}`
  1. Guardrail: check prompt against stop-word list; log and reject if triggered
  2. Build messages: system prompt + context_code + user prompt
  3. Call OpenRouter via AsyncOpenAI
  4. Persist `LLMInteraction` row (prompt, response, model_id, tokens, cost, latency)
  5. Return `{response_text, model_id, cost_usd}`

- Stop-word filter: simple list check on lowercased prompt (e.g. `["rm -rf", "subprocess", "os.system", ...]` — tunable)
- API key from env var `OPENROUTER_API_KEY`

---

### Step 8 — Frontend Foundation

`frontend/vite.config.ts`: proxy `/api` → `http://localhost:8000`

`frontend/src/api/client.ts`: typed `apiFetch` wrapper that handles 401 → redirect to login.

`frontend/src/App.tsx`: React Router routes:
- `/login` — Login page
- `/` — ScriptCatalog
- `/editor/new` — ScriptEditor (new blank)
- `/editor/:id` — ScriptEditor (existing script)

`frontend/src/contexts/AuthContext.tsx`: session state (`user`, `roles`), `login()`, `logout()`.

---

### Step 9 — Script Catalog UI

File: `frontend/src/components/ScriptCatalog/`

- Fetch `GET /api/scripts` on mount
- Table rows: `ordering_number` | `descriptive_name` | `version` | `last_run` (time + Success/Failure badge)
- Hover tooltip: full docstring, `last_modified`, version
- "+" button top-right → navigate `/editor/new`
- Row click → navigate `/editor/:id`
- Viewer-only users: see catalog but no "+" button

---

### Step 10 — Script Editor UI

File: `frontend/src/components/ScriptEditor/`

**Monaco Editor:**
- `@monaco-editor/react` wrapper
- Language: `python`, theme: `vs-dark`
- On mount: load script content from `GET /api/scripts/:id`

**LanguageService abstraction (`frontend/src/services/LanguageService.ts`):**
```typescript
interface LanguageService {
  getDiagnostics(model: monaco.editor.ITextModel): Promise<monaco.editor.IMarkerData[]>
  // Phase 2: getCompletions, getHover — add here without touching editor code
}
```

**Phase 1 implementation** — `PyrightWorkerLanguageService`:
- Spawn Pyright browser worker (`pyright/dist/pyright.browser.js` as a Web Worker)
- Use `monaco-languageclient` with a Web Worker message transport to connect Monaco to Pyright worker
- Surfaces diagnostics (red squiggles) in Monaco

Hook: `useLanguageService(editorRef) → LanguageService` — creates worker, configures Monaco markers on change.

**Editor controls panel:**
- Save (PUT /api/scripts/:id), Fork (POST /api/scripts/:id/fork), Bump Major, Run (POST /api/execute/:id)
- Version badge: `v{major}.{minor}` — clicking shows version history list

**LLM prompt panel (bottom or right sidebar):**
- Textarea for user prompt
- Submit → POST /api/llm/complete with current code as context
- Response shown in panel; "Insert into editor" button appends/replaces editor content

---

### Step 11 — Static File Serving

`backend/app/main.py`:
```python
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

For production: `npm run build` outputs to `frontend/dist/`, FastAPI serves it.
For dev: Vite dev server handles frontend, proxies `/api` to FastAPI.

---

### Step 12 — Testing & Stabilization

Backend tests (`pytest`):
- `test_auth.py` — login, logout, role enforcement
- `test_scripts.py` — create, save (version increment), fork, ordering_number assignment
- `test_versioning.py` — Major.Minor logic edge cases, git commits
- `test_execution.py` — single run, group concurrency (mock Docker)
- `test_llm.py` — stop-word filter, LLM logging (mock OpenRouter)

Manual E2E checklist:
- Login as `ed1`, create script, edit, save (version bumps), run
- Login as `mo1`, confirm read-only (no save/fork buttons)
- Fork a script, verify parent recorded
- Run all scripts, verify group concurrency
- LLM prompt → response → insert into editor

---

## Key Libraries

| Layer | Library | Purpose |
|---|---|---|
| Frontend | `@monaco-editor/react` | Monaco React wrapper |
| Frontend | `monaco-languageclient` | LSP client for Monaco |
| Frontend | `pyright` | Browser bundle for Pyright worker |
| Frontend | `react-router-dom` v7 | Routing |
| Backend | `fastapi` + `uvicorn` | Web framework |
| Backend | `sqlmodel` | ORM (SQLite) |
| Backend | `gitpython` | Git operations |
| Backend | `openai` | OpenRouter via AsyncOpenAI |
| Backend | `docker` (Python SDK) | Container execution |
| Backend | Starlette `SessionMiddleware` | Signed cookie sessions |

---

## Verification

1. `cd backend && uv run uvicorn app.main:app --reload` starts without error
2. `cd frontend && npm run dev` starts Vite on :5173
3. Navigate to `http://localhost:5173/login` — login as `ed1:1editor`
4. Script catalog loads, "+" creates a new script with ordering_number `1.0`
5. Monaco editor opens with Pyright diagnostics active (squiggles on syntax errors)
6. Save increments minor version (0.1 → 0.2)
7. Run executes script in Docker, output displayed
8. LLM prompt returns code suggestion; inserting it into Monaco works
9. Login as `mo1:2viewer` — save/run buttons absent; catalog is read-only
10. `pytest backend/` passes all tests
