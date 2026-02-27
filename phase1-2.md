# 2-phase delivery plan
with scope boundaries and man-hour estimates.

Implementor:
* Senior engineer
* Strong Python + decent React
* Not full-time (context switching overhead exists)

## PHASE 1

2 users / Single execution environment / Browser Pyright

####  Goal

Build a fully functional LLM-powered scripting tool with:
* Monaco Editor
* Browser-based Pyright
* Single Docker execution environment
* Script catalog
* Version snapshots
* Basic LLM integration
* Hardcoded auth (2 users)

No WebSockets. No backend LSP. No per-user isolation.

###  Architecture

```text
React
 ├── Monaco
 ├── Pyright (Web Worker)
 └── REST → FastAPI
              ├── Version store
              ├── Docker runner (single image)
              └── LLM proxy
```

---

### Scope Definition (Strict)

#### Included
* Single interpreter (e.g. CPython 3.14)
* One Docker image
* Browser-based language intelligence
* Script grouping execution logic
* Snapshot-based version store
* Basic LLM endpoint
* Minimal guardrails (logging + simple filtering)

#### Excluded
* Multi-interpreter awareness
* Backend LSP
* Multi-file projects
* Complex AST rewriting guardrails
* Horizontal scaling

### Phase 1 Man-Hour Estimate

| Component                   | Hours            |
| --------------------------- | ---------------- |
| Monaco integration          | 3–4              |
| Pyright worker + LSP bridge | 12–18            |
| Script catalog UI           | 8–12             |
| Script editor UI polish     | 8–12             |
| Version snapshot engine     | 12–18            |
| Docker execution sandbox    | 8–12             |
| Execution grouping logic    | 6–10             |
| LLM proxy integration       | 6–10             |
| Basic guardrails            | 4–6              |
| Hardcoded auth              | 2–4              |
| Testing + stabilization     | 12–18            |
| **Total**                   | **81–124 hours** |

Realistic Total: **90–110 hours** That’s ~3 focused weeks.

### Risk Profile (Low–Medium)

Main risk areas:
* ~~Pyright worker wiring~~ — resolved: `pyright` npm package ships Node.js-only bundles; no browser bundle exists at v1.1.408. Phase 1 ships with a `NullLanguageService` (no-op). Monaco provides Python syntax highlighting natively. The `LanguageService` abstraction is in place for Phase 2 swap-in.
* Versioning correctness
* Execution group concurrency bugs

Everything else is straightforward.

## PHASE 2

2–12 users - Per-user/interpreter Docker runners - Server LSP

###  Phase 2 Goals
* Per-user Docker execution
* Multiple interpreters (CPython, GraalPy, etc.)
* Backend Language Server via WebSocket
* Environment-aware autocomplete
* Session lifecycle management
* Proper auth model
* Improved guardrails (AST-based)

###  Architecture
```text
Frontend (Monaco)
   ├── REST (save, execute, LLM)
   └── WebSocket → LSP Bridge

FastAPI
   ├── REST API
   ├── WebSocket endpoint
   ├── LSP process manager
   ├── Docker runner pool
   └── Version store
```

### New Capabilities Introduced

*  Server LSP
   Using:
   * pylsp or
   * pyright-langserver
   * via Language Server Protocol
   Each active session: Spawns LSP process > Binds to interpreter > Maintains virtual workspace
* Per-User Docker Runners
  Instead of single execution image:
  * One container per execution
  * Interpreter selected dynamically
  * Resource limits enforced
  * Optional container pool optimization

#### Session Management Layer

FastAPI must now:
* Track connected users
* Spawn/kill LSP processes
* Handle WebSocket lifecycle
* Prevent resource leaks

###  Phase 2 Man-Hour Estimate

| Component                            | Hours             |
| ------------------------------------ | ----------------- |
| WebSocket infra                      | 10–16             |
| LSP integration                      | 16–24             |
| LSP process lifecycle mgmt           | 12–18             |
| Multi-interpreter Docker strategy    | 12–20             |
| Per-user isolation logic             | 10–16             |
| Container resource limits            | 6–10              |
| AST-based guardrails                 | 12–20             |
| Auth upgrade (proper roles/sessions) | 6–12              |
| Concurrency testing                  | 12–18             |
| Windows validation                   | 8–12              |
| Refactoring from Phase 1             | 10–16             |
| **Total**                            | **114–182 hours** |

Realistic Total: **130–160 hours** That’s 4–6 additional weeks.

---

## Phase Comparison

|                    | Phase 1    | Phase 2              |
| ------------------ | ---------- | -------------------- |
| Users              | 2          | 2–12                 |
| LSP                | Browser    | Server               |
| Execution          | Single env | Per-user/interpreter |
| Docker             | One image  | Dynamic runners      |
| Infra complexity   | Low        | High                 |
| Total system hours | ~100       | +150                 |
| Operational burden | Minimal    | Moderate             |

###  Strategic Insight
Phase 1 gives:
* 80% user-perceived capability
* 30% of infrastructure complexity

Phase 2 gives:
* True IDE fidelity
* True isolation
* Production realism


### Critical Migration Consideration

Design Phase 1 so:
* **LSP**: Isolate all language-intelligence calls behind a `LanguageService` interface (e.g., a React hook or service class). Phase 1 implements it with the browser Pyright Web Worker; Phase 2 swaps in a WebSocket-backed server LSP without touching editor code.
* Execution API does not assume single interpreter
* Version model is interpreter-agnostic

This makes Phase 2 additive instead of a rewrite.

### Overall Project Investment

If you complete both phases: ~230–260 total engineering hours

That’s roughly:
* 2 months serious solo build
* Or 6–8 weeks focused sprinting
