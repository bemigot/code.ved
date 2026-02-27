"""Tests for script CRUD, ordering, fork, merge endpoints."""


def test_create_script_returns_201(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    assert r.status_code == 201


def test_create_script_ordering_number(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    assert r.json()["ordering_number"] == 1.0


def test_create_script_initial_version(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    v = r.json()["version"]
    assert v["major"] == 0
    assert v["minor"] == 1


def test_create_script_descriptive_name_from_docstring(ed1):
    r = ed1.post("/api/scripts", json={"content": '"""My Script\nDoes stuff.\n"""'})
    assert r.json()["descriptive_name"] == "My Script"


def test_create_script_untitled_when_no_docstring(ed1):
    r = ed1.post("/api/scripts", json={"content": "x = 1"})
    assert r.json()["descriptive_name"] == "Untitled"


def test_second_script_gets_ordering_number_2(ed1):
    ed1.post("/api/scripts", json={"content": ""})
    r = ed1.post("/api/scripts", json={"content": ""})
    assert r.json()["ordering_number"] == 2.0


def test_get_script_returns_content(ed1):
    r = ed1.post("/api/scripts", json={"content": "y = 42"})
    sid = r.json()["id"]
    r2 = ed1.get(f"/api/scripts/{sid}")
    assert r2.status_code == 200
    assert r2.json()["content"] == "y = 42"


def test_get_nonexistent_script_returns_404(ed1):
    r = ed1.get("/api/scripts/9999")
    assert r.status_code == 404


def test_list_scripts_returns_all(ed1):
    ed1.post("/api/scripts", json={"content": ""})
    ed1.post("/api/scripts", json={"content": ""})
    r = ed1.get("/api/scripts")
    assert len(r.json()) == 2


def test_list_scripts_sorted_by_ordering_number(ed1):
    ed1.post("/api/scripts", json={"content": ""})
    ed1.post("/api/scripts", json={"content": ""})
    scripts = ed1.get("/api/scripts").json()
    nums = [s["ordering_number"] for s in scripts]
    assert nums == sorted(nums)


def test_save_script_increments_minor(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    r2 = ed1.put(f"/api/scripts/{sid}", json={"content": "x = 1"})
    assert r2.status_code == 200
    v = r2.json()["version"]
    assert v["major"] == 0
    assert v["minor"] == 2


def test_save_script_preserves_major(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    ed1.put(f"/api/scripts/{sid}", json={"content": "a"})
    r2 = ed1.put(f"/api/scripts/{sid}", json={"content": "b"})
    assert r2.json()["version"]["major"] == 0


def test_bump_major_increments_major(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/bump-major")
    assert r2.status_code == 200
    v = r2.json()["version"]
    assert v["major"] == 1
    assert v["minor"] == 0


def test_fork_creates_new_script(ed1):
    r = ed1.post("/api/scripts", json={"content": "a = 1"})
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/fork")
    assert r2.status_code == 201
    assert r2.json()["id"] != sid


def test_fork_copies_content(ed1):
    r = ed1.post("/api/scripts", json={"content": "hello = True"})
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/fork")
    assert r2.json()["content"] == "hello = True"


def test_fork_records_parent_refs(ed1):
    r = ed1.post("/api/scripts", json={"content": "a = 1"})
    sid = r.json()["id"]
    vid = r.json()["version"]["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/fork")
    v = r2.json()["version"]
    assert v["parent_script_id"] == sid
    assert v["parent_version_id"] == vid


def test_fork_gets_next_ordering_number(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/fork")
    assert r2.json()["ordering_number"] == 2.0


def test_merge_returns_ok(ed1):
    r = ed1.post("/api/scripts", json={"content": "z = 3"})
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/merge")
    assert r2.status_code == 200
    assert r2.json()["ok"] is True


def test_list_versions_returns_history(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    ed1.put(f"/api/scripts/{sid}", json={"content": "a"})
    ed1.put(f"/api/scripts/{sid}", json={"content": "b"})
    versions = ed1.get(f"/api/scripts/{sid}/versions").json()
    assert len(versions) == 3  # 0.1, 0.2, 0.3


def test_viewer_cannot_create(mo1):
    r = mo1.post("/api/scripts", json={"content": ""})
    assert r.status_code == 403


def test_viewer_can_read(mo1, ed1):
    r = ed1.post("/api/scripts", json={"content": "x = 1"})
    sid = r.json()["id"]
    # mo1 uses a different TestClient instance (different session cookie)
    # but shares the same DB — so viewer can read the script created by editor
    r2 = mo1.get(f"/api/scripts/{sid}")
    assert r2.status_code == 200
