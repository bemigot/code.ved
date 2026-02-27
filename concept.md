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
    - Scripts are assigned a unique numeric `ordering_number` (e.g., `5.33`). The backend hints the next available slot when setting the ordering.
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
    - Users can create a new script based on the current one.
    - Users can explicitly increment the `Major` version number by one. New scripts start with `Major` 0.
    - The `Minor` version is automatically incremented by the backend upon saving changes.
- **Backend Interaction**:
    - On save, the backend validates the script.
    - The backend may return an error if the saved content is identical to an existing script in the shared repository. This is a desirable restriction for the shared task queue, currently under design.

**Scripting language LSP Note**: Backend runs Python Language Server, Frontend connects via WebSocket.
This way the client has true environment-aware autocomplete, and installed package awareness.

- **Implementation Note**: This architecture requires two key components.
    - **Frontend**: A library such as `monaco-languageclient` will be used to connect the editor instance to the backend WebSocket.
    - **Backend**: The FastAPI application must manage a stateful WebSocket endpoint. This endpoint will be responsible for spawning and managing the lifecycle of a dedicated LSP process (e.g., `pylsp`, `pyright-langserver`) for each active user session.

## 3. Backend Architecture

The backend is primarily a FastAPI application responsible for business logic, script execution, and serving the frontend.

### 3.1. Script and Version Management
- The backend maintains a version control system for all scripts, storing every version as an immutable snapshot, conceptually similar to Git.
- It tracks script metadata, including version numbers, committer, modification date and time with 0.01 s precision.
- For each script, the backend stores associated test inputs (e.g., a JSON string).

### 3.2. Script Execution Engine
- **Sandbox Environment**: Scripts are executed in an isolated sandbox to ensure security and reproducibility.
  The backend assesses available script interpreters (e.g., CPython 3.14, GraalPy) and allows the user to select one for execution.
  A list of available interpreters will be provided in the new script template.
- **Execution Logic**:
    - The system can run a single script on demand.
    - The system can execute all scripts sequentially based on their `ordering_number`.
    - **Concurrency**: Scripts with the same integer part of their `ordering_number` (e.g., `3.01`, `3.99`) are considered part of the same execution group and may be run concurrently. Groups are executed sequentially (e.g., all `2.xx` scripts complete before any `3.xx` scripts begin).
- **Results**: The output of the last successful run and the results of the last full execution pass are persisted.

### 3.3. LLM and API Services
- **LLM Integration**: The backend exposes an endpoint that receives user prompts from the frontend. It logs, validates and preprocesses these prompts before forwarding them to an LLM provider (e.g., via OpenRouter). It will handle any tool-use requests from the LLM and manage API-related metrics like cost and performance.
- **LLM Guardrails**: The backend refuses to forward suspicious-looking code or prompts to the LLM in order to prevent data leaks and attacks on the LLM. For starters, the filtering will be based on a stop-word list and package/function/variable name rewriting rules.
- **Static File Serving**: The FastAPI application serves the compiled static assets (HTML, JS, CSS) of the React frontend.

- **Implementation Note**: The LLM Guardrails feature has significant complexity.
    - **Stop-word filtering** is simple to implement but may be ineffective or overly restrictive, requiring careful tuning.
    - **Name rewriting** is a more robust approach but is non-trivial. A simple text replacement is brittle and likely to break code. A reliable implementation (Target Phase 2: Advanced stage) will require parsing the code into an Abstract Syntax Tree (AST) to intelligently identify and pseudonymize sensitive identifiers.

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
