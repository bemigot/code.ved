"""Tests for the LLM proxy: stop-word filter, logging, role enforcement."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Session, select

from app.models import LLMInteraction


def _make_completion(text: str = "Fixed code", model: str = "gpt-4o") -> MagicMock:
    choice = MagicMock()
    choice.message.content = text
    completion = MagicMock()
    completion.choices = [choice]
    completion.model = model
    completion.usage.prompt_tokens = 10
    completion.usage.completion_tokens = 20
    completion.usage.total_cost = 0.001
    return completion


@pytest.fixture()
def mock_llm():
    """Replace _get_client() so no real network call is made."""
    client_mock = MagicMock()
    client_mock.chat.completions.create = AsyncMock(return_value=_make_completion())
    with patch("app.routes.llm._get_client", return_value=client_mock):
        yield client_mock


# ── Stop-word filter ──────────────────────────────────────────────────────────

def test_stop_word_os_system_rejected(ed1):
    r = ed1.post("/api/llm/complete", json={
        "prompt": "use os.system to run something",
        "context_code": "",
    })
    assert r.status_code == 400
    assert "os.system" in r.json()["detail"]


def test_stop_word_rm_rf_rejected(ed1):
    r = ed1.post("/api/llm/complete", json={
        "prompt": "run rm -rf /tmp to clean up",
        "context_code": "",
    })
    assert r.status_code == 400


def test_stop_word_check_is_case_insensitive(ed1):
    r = ed1.post("/api/llm/complete", json={
        "prompt": "use OS.SYSTEM to run a command",
        "context_code": "",
    })
    assert r.status_code == 400


def test_rejected_prompt_logs_interaction(ed1, db_engine):
    ed1.post("/api/llm/complete", json={
        "prompt": "rm -rf everything",
        "context_code": "",
    })
    with Session(db_engine) as session:
        rows = session.exec(select(LLMInteraction)).all()
    assert len(rows) == 1
    assert "REJECTED" in rows[0].response
    assert rows[0].model_id == "none"
    assert rows[0].cost_usd == 0.0


# ── Valid prompts ─────────────────────────────────────────────────────────────

def test_valid_prompt_returns_response(ed1, mock_llm):
    r = ed1.post("/api/llm/complete", json={
        "prompt": "What does this script do?",
        "context_code": "x = 1",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["response_text"] == "Fixed code"
    assert "model_id" in data
    assert "cost_usd" in data


def test_valid_prompt_logs_interaction(ed1, mock_llm, db_engine):
    ed1.post("/api/llm/complete", json={
        "prompt": "Explain this code",
        "context_code": "y = 2",
    })
    with Session(db_engine) as session:
        rows = session.exec(select(LLMInteraction)).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.prompt == "Explain this code"
    assert row.response == "Fixed code"
    assert row.input_tokens == 10
    assert row.output_tokens == 20


def test_llm_cost_recorded(ed1, mock_llm, db_engine):
    ed1.post("/api/llm/complete", json={"prompt": "help", "context_code": ""})
    with Session(db_engine) as session:
        rows = session.exec(select(LLMInteraction)).all()
    assert rows[0].cost_usd == pytest.approx(0.001)


def test_viewer_cannot_use_llm(mo1):
    r = mo1.post("/api/llm/complete", json={"prompt": "help", "context_code": ""})
    assert r.status_code == 403


def test_unauthenticated_cannot_use_llm(client):
    r = client.post("/api/llm/complete", json={"prompt": "help", "context_code": ""})
    assert r.status_code == 401
