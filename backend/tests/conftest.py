"""Shared fixtures for the test suite.

Each test gets:
  - a fresh in-memory SQLite database (overrides get_session dependency)
  - an isolated git repo in a temp dir (monkeypatches SCRIPTS_REPO_PATH)
  - an unauthenticated TestClient (`client`)
  - pre-authenticated clients (`ed1`, `mo1`)
"""
from collections.abc import Generator
from datetime import datetime

import pytest
from sqlmodel import Session, SQLModel, create_engine
from starlette.testclient import TestClient

import app.git_store as git_store_module
from app.db import get_session
from app.main import app
from app.models import Execution


# ── Database ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/test.db", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


# ── TestClient (unauthenticated) ──────────────────────────────────────────────

@pytest.fixture()
def client(db_engine, tmp_path, monkeypatch):
    # Redirect git repo to an isolated temp dir
    repo_path = tmp_path / "scripts_repo"
    monkeypatch.setattr(git_store_module, "SCRIPTS_REPO_PATH", repo_path)

    # Override DB session with the test engine
    def _get_test_session() -> Generator[Session, None, None]:
        with Session(db_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_test_session

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.pop(get_session, None)


# ── Authenticated clients ─────────────────────────────────────────────────────

@pytest.fixture()
def ed1(client):
    r = client.post("/api/auth/login", json={"username": "ed1", "password": "1editor"})
    assert r.status_code == 200
    return client


@pytest.fixture()
def mo1(client):
    r = client.post("/api/auth/login", json={"username": "mo1", "password": "2viewer"})
    assert r.status_code == 200
    return client


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_execution(version_id: int = 1, exit_code: int = 0) -> Execution:
    """Build an Execution object as if it were returned by docker_runner."""
    exe = Execution(
        script_version_id=version_id,
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        exit_code=exit_code,
        stdout="hello",
        stderr="",
        interpreter="cpython-3.14",
    )
    exe.id = 99  # simulate auto-assigned PK
    return exe
