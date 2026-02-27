"""Tests for Major.Minor versioning logic and git commit tracking."""


def test_initial_version_is_0_1(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    v = r.json()["version"]
    assert v["major"] == 0
    assert v["minor"] == 1


def test_saves_increment_minor_in_sequence(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    for expected_minor in [2, 3, 4, 5]:
        r = ed1.put(f"/api/scripts/{sid}", json={"content": f"x = {expected_minor}"})
        assert r.json()["version"]["minor"] == expected_minor


def test_saves_keep_major_unchanged(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    ed1.put(f"/api/scripts/{sid}", json={"content": "a"})
    r2 = ed1.put(f"/api/scripts/{sid}", json={"content": "b"})
    assert r2.json()["version"]["major"] == 0


def test_bump_major_resets_minor_to_zero(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    ed1.put(f"/api/scripts/{sid}", json={"content": "v1"})  # → 0.2
    r2 = ed1.post(f"/api/scripts/{sid}/bump-major")
    v = r2.json()["version"]
    assert v["major"] == 1
    assert v["minor"] == 0


def test_save_after_bump_produces_x_1(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    ed1.post(f"/api/scripts/{sid}/bump-major")  # → 1.0
    r2 = ed1.put(f"/api/scripts/{sid}", json={"content": "new content"})
    v = r2.json()["version"]
    assert v["major"] == 1
    assert v["minor"] == 1


def test_multiple_bumps(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    ed1.post(f"/api/scripts/{sid}/bump-major")  # → 1.0
    ed1.post(f"/api/scripts/{sid}/bump-major")  # → 2.0
    r2 = ed1.post(f"/api/scripts/{sid}/bump-major")  # → 3.0
    assert r2.json()["version"]["major"] == 3


def test_fork_records_parent_script_id(ed1):
    r = ed1.post("/api/scripts", json={"content": "parent"})
    parent_id = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{parent_id}/fork")
    assert r2.json()["version"]["parent_script_id"] == parent_id


def test_fork_records_parent_version_id(ed1):
    r = ed1.post("/api/scripts", json={"content": "parent"})
    parent_vid = r.json()["version"]["id"]
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/fork")
    assert r2.json()["version"]["parent_version_id"] == parent_vid


def test_fork_starts_at_version_0_1(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    r2 = ed1.post(f"/api/scripts/{sid}/fork")
    v = r2.json()["version"]
    assert v["major"] == 0
    assert v["minor"] == 1


def test_versions_list_is_newest_first(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    ed1.put(f"/api/scripts/{sid}", json={"content": "a"})
    ed1.put(f"/api/scripts/{sid}", json={"content": "b"})
    versions = ed1.get(f"/api/scripts/{sid}/versions").json()
    minors = [v["minor"] for v in versions]
    assert minors == sorted(minors, reverse=True)


def test_git_commit_hash_is_40_chars(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    assert len(r.json()["version"]["git_commit_hash"]) == 40


def test_bump_major_reuses_last_commit_hash(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    original_hash = r.json()["version"]["git_commit_hash"]
    r2 = ed1.post(f"/api/scripts/{sid}/bump-major")
    # bump-major doesn't write to git — same hash as the last real commit
    assert r2.json()["version"]["git_commit_hash"] == original_hash


def test_save_produces_different_commit_hash(ed1):
    r = ed1.post("/api/scripts", json={"content": ""})
    sid = r.json()["id"]
    hash1 = r.json()["version"]["git_commit_hash"]
    r2 = ed1.put(f"/api/scripts/{sid}", json={"content": "new"})
    hash2 = r2.json()["version"]["git_commit_hash"]
    assert hash1 != hash2
