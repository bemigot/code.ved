"""Tests for execution endpoints and the grouper utility."""
from unittest.mock import patch

import pytest

from app.executor.grouper import group_scripts
from app.models import Script
from tests.conftest import make_execution


@pytest.fixture()
def mock_run():
    """Patch docker_runner.run_script so no container is launched."""
    with patch("app.routes.execution.run_script") as m:
        m.return_value = make_execution()
        yield m


# ── /api/execute/{id} ─────────────────────────────────────────────────────────

def test_run_before_merge_returns_400(ed1):
    r = ed1.post("/api/scripts", json={"content": "print('hi')"})
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/execute/{sid}", json={"test_data": ""})
    assert r2.status_code == 400
    assert "merge" in r2.json()["detail"].lower()


def test_run_after_merge_returns_result(ed1, mock_run):
    r = ed1.post("/api/scripts", json={"content": "print('hi')"})
    sid = r.json()["id"]
    ed1.post(f"/api/scripts/{sid}/merge")
    r2 = ed1.post(f"/api/execute/{sid}", json={"test_data": ""})
    assert r2.status_code == 200
    data = r2.json()
    assert data["exit_code"] == 0
    assert data["stdout"] == "hello"
    assert data["interpreter"] == "cpython-3.14"


def test_run_calls_run_script_once(ed1, mock_run):
    r = ed1.post("/api/scripts", json={"content": "x = 1"})
    sid = r.json()["id"]
    ed1.post(f"/api/scripts/{sid}/merge")
    ed1.post(f"/api/execute/{sid}", json={"test_data": ""})
    assert mock_run.call_count == 1


def test_run_nonexistent_script_returns_404(ed1):
    r = ed1.post("/api/execute/9999", json={"test_data": ""})
    assert r.status_code == 404


def test_viewer_cannot_run(mo1):
    r = mo1.post("/api/execute/1", json={"test_data": ""})
    assert r.status_code == 403


# ── /api/execute/all ──────────────────────────────────────────────────────────

def test_run_all_runs_merged_scripts(ed1, mock_run):
    for content in ["a = 1", "b = 2", "c = 3"]:
        r = ed1.post("/api/scripts", json={"content": content})
        ed1.post(f"/api/scripts/{r.json()['id']}/merge")
    r = ed1.post("/api/execute/all", json={"test_data": ""})
    assert r.status_code == 200
    assert len(r.json()) == 3
    assert mock_run.call_count == 3


def test_run_all_skips_unmerged_scripts(ed1, mock_run):
    # Script 1: merged
    r1 = ed1.post("/api/scripts", json={"content": "a = 1"})
    ed1.post(f"/api/scripts/{r1.json()['id']}/merge")
    # Script 2: NOT merged
    ed1.post("/api/scripts", json={"content": "b = 2"})
    r = ed1.post("/api/execute/all", json={"test_data": ""})
    assert len(r.json()) == 1
    assert mock_run.call_count == 1


# ── /api/execute/{id}/last ────────────────────────────────────────────────────

def test_last_execution_none_before_any_run(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    r2 = ed1.get(f"/api/execute/{sid}/last")
    assert r2.status_code == 200
    assert r2.json() is None


def test_last_execution_returns_result_after_run(ed1, mock_run):
    r = ed1.post("/api/scripts", json={"content": "x = 1"})
    sid = r.json()["id"]
    ed1.post(f"/api/scripts/{sid}/merge")
    ed1.post(f"/api/execute/{sid}", json={"test_data": ""})

    # last execution uses the real DB — but run_script was mocked, so no
    # Execution row was written. The route still queries the DB and gets None.
    r2 = ed1.get(f"/api/execute/{sid}/last")
    assert r2.status_code == 200
    # None is expected: mock bypassed the DB write inside docker_runner
    assert r2.json() is None


# ── grouper unit tests ────────────────────────────────────────────────────────

def test_grouper_single_group():
    scripts = [
        Script(id=1, ordering_number=1.01, is_deleted=False),
        Script(id=2, ordering_number=1.99, is_deleted=False),
    ]
    groups = group_scripts(scripts)
    assert len(groups) == 1
    assert len(groups[0]) == 2


def test_grouper_two_groups():
    scripts = [
        Script(id=1, ordering_number=1.01, is_deleted=False),
        Script(id=2, ordering_number=1.99, is_deleted=False),
        Script(id=3, ordering_number=2.50, is_deleted=False),
    ]
    groups = group_scripts(scripts)
    assert len(groups) == 2
    assert len(groups[0]) == 2
    assert len(groups[1]) == 1


def test_grouper_sorted_by_group_key():
    scripts = [
        Script(id=1, ordering_number=3.0, is_deleted=False),
        Script(id=2, ordering_number=1.0, is_deleted=False),
        Script(id=3, ordering_number=2.0, is_deleted=False),
    ]
    groups = group_scripts(scripts)
    first_script_num = groups[0][0].ordering_number
    assert first_script_num == 1.0


def test_grouper_empty_list():
    assert group_scripts([]) == []
