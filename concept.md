# LLM-Powered Python Scripting Environment

## 1. Project Overview

This document outlines the concept for a prototype web application designed
for the creation and management of Python scripts, augmented by a Large Language Model (LLM).

This document describes the target architecture of the final system. Some implementation details
(e.g., specific LSP integration methods) may evolve through incremental development phases.

The application is intended for local execution on a developer's machine,
with initial development targeting Linux and subsequent validation on Windows.

### 1.1. Core Technologies
- **Python Management**: `uv`
- **Node.js**: v24 (already installed on the developer's machine), package management - `npm`
- **Frontend**: React 19
- **Backend**: FastAPI

## 2. Frontend Architecture

The frontend is a component-based single-page application (SPA) built with React 19.

### 2.1. Script Catalog Component

This component serves as the main dashboard for viewing and managing scripts.

- **Functionality**:
    - Displays a list of all managed Python scripts.
    - Scripts are assigned a unique numeric `ordering_number` (e.g., `5.33`). Each new script receives the next available integer as its Major number (e.g., the script after the last `3.xx` entry gets `4.0`). Fine-grained reordering logic is deferred to a later stage.
    - Provides a "+" button to open the Script Editor with a new script template.
- **Script Entry Details**:
    - **Primary Display**: Each script is listed with its `ordering_number` and a `descriptive_name`
      (derived from the first line of the script's docstring).
    - **Status**: Indicates the last execution time and result (`Success`/`Failure`).
    - **Tooltip Metadata**: A tooltip provides additional details:
        - `version`: A `Major.Minor` version number (e.g., `1.23`). The Major version is
          user-controlled, while the Minor version is auto-incremented on each modification.
        - `last_modified`: The timestamp of the last modification (from the custom version control system).
        - `description`: The full docstring of the script.
- **Interaction**: Users can select a script to open it in the Script Editor component.

### 2.2. Script Editor Component

This component provides an integrated development environment (IDE) experience for viewing and editing scripts.

- **Core Functionality**:
    - **Editor**: Utilizes the Monaco Editor to provide a VSCode-like experience,
      including syntax highlighting, error display, enforcing code style.
    - **LLM Interaction**: An integrated prompt window allows the user to submit natural language
      instructions for code creation/modification to the backend LLM service.
- **Versioning**:
    - Users can fork the current script. The fork is placed in the editor's personal branch; SQLite records its origin (parent script ID + version).
    - Users can explicitly increment the `Major` version number by one. New scripts start at version `0.1` on first save.
    - The `Minor` version is automatically incremented by the backend upon saving changes.
- **Backend Interaction**:
    - On save, the backend validates the script.
    - Duplicate-content detection across the shared queue is deferred to Phase 2.

**Scripting language LSP Note**: Backend runs Python Language Server, Frontend connects via WebSocket.
This way the client has true environment-aware autocomplete, and installed package awareness.

- **Implementation Note**: This architecture requires two key components.
    - **Frontend**: A library such as `monaco-languageclient` will be used to connect the editor instance to the backend WebSocket.
    - **Backend**: The FastAPI application must manage a stateful WebSocket endpoint. This endpoint will be responsible for spawning and managing the lifecycle of a dedicated LSP process (e.g., `pylsp`, `pyright-langserver`) for each active user session.

## 3. Backend Architecture

The backend is primarily a FastAPI application responsible for business logic, script execution, and serving the frontend.

### 3.1. Script and Version Management
- Scripts are stored in a real Git repository. A shared `prod` branch holds the authoritative execution queue; each editor has a personal branch (Phase 1: `ed1` only).
- A SQLite database stores all metadata: version numbers (`Major.Minor`), committer, timestamps with 0.01 s precision, and fork origin (parent script ID + version) for forked scripts.
- LLM interactions are logged in SQLite: prompt sent, raw model response, model identifier, and cost metrics — each record linked to the script version it produced.
- For each script, the backend stores associated test data. At execution time the runner writes this data to a temporary file and passes the path as the first positional argument (see §3.2).

> **Design Note — Duplicate Content Policy (deferred to Phase 2)**
> The `prod` branch must not contain two distinct scripts whose executable code is identical. "Executable code" excludes comments and docstrings: two versions of the *same* script that differ only in non-executable content are valid and permitted as distinct version history entries. The precise comparison algorithm (e.g., AST-normalised hash) and the enforcement point (pre-merge check, save validation, or a periodic audit) are open questions to be settled in Phase 2.

### 3.2. Script Execution Engine
- **Sandbox Environment**: Scripts are executed in an isolated sandbox to ensure security and reproducibility.
  The backend assesses available script interpreters (e.g., CPython 3.14, GraalPy) and allows the user to select one for execution.
  A list of available interpreters will be provided in the new script template.
- **Execution Logic**:
    - The system can run a single script on demand.
    - The system can execute all scripts sequentially based on their `ordering_number`.
    - **Concurrency**: Scripts with the same integer part of their `ordering_number` (e.g., `3.01`, `3.99`) are considered part of the same execution group and may be run concurrently. Groups are executed sequentially (e.g., all `2.xx` scripts complete before any `3.xx` scripts begin).
    - **Script Input**: Scripts receive data via positional CLI arguments only — no option parsing. The runner writes the test or production dataset to a temporary file and passes the file path as the first positional argument.
- **Results**: The output of the last successful run and the results of the last full execution pass are persisted.

### 3.3. LLM and API Services
- **LLM Integration**: The backend exposes an endpoint that receives user prompts from the frontend. It logs, validates, and preprocesses these prompts before forwarding them to **OpenRouter** via `openai.AsyncOpenAI` (configured with OpenRouter's base URL). It handles tool-use requests from the LLM and records cost and latency metrics in SQLite.
- **LLM Tool Scope**: The LLM may be granted read access to: the active Python interpreter version, installed module signatures, and usage examples. Sensitive identifiers pass through an anonymization pipeline before transmission and are restored afterward. No filesystem access is granted except, optionally, gated read-only access to a designated sandbox directory.
- **LLM Guardrails**:
    - **Phase 1**: All prompts and responses are logged. A stop-word filter blocks obviously suspicious content. Simple to implement; requires tuning to avoid false positives.
    - **Phase 2**: AST-based identifier pseudonymization. The script is parsed into an Abstract Syntax Tree to intelligently rename sensitive identifiers before transmission and restore them afterward. Non-trivial but robust against brittle text-replacement failures.
- **Static File Serving**: The FastAPI application serves the compiled static assets (HTML, JS, CSS) of the React frontend.

### 3.4. Authentication and Authorization
- **Roles**: Phase-1: Two user roles are defined: `viewer` and `editor`.
- **Users**: Phase-1: Two hardcoded users are configured for the prototype:
    - `ed1`: Has both `viewer` and `editor` roles (password: `1editor`).
    - `mo1`: Has the `viewer` role only (password: `2viewer`).

### 3.5 Phase 2: Cooperative editing
- Phase 2 adds 3 more users with `editor` role.
- The "run all" pipeline(s) is (are) shared by all users, as well as script repository.
- Individual scripts may be run in a per-user sandboxed environment
- Per-user "branch" and conflict prevention/notification protocol to be defined later.
