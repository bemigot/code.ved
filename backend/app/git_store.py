from pathlib import Path

from git import Repo

SCRIPTS_REPO_PATH = Path(__file__).parent.parent / "scripts_repo"


def init_repo() -> None:
    """Ensure scripts_repo exists with prod and ed1 branches."""
    if (SCRIPTS_REPO_PATH / ".git").exists():
        repo = Repo(SCRIPTS_REPO_PATH)
    else:
        SCRIPTS_REPO_PATH.mkdir(parents=True, exist_ok=True)
        repo = Repo.init(SCRIPTS_REPO_PATH)
        (SCRIPTS_REPO_PATH / ".gitkeep").write_text("")
        repo.index.add([".gitkeep"])
        repo.index.commit("init")

    existing = {b.name for b in repo.heads}
    if "prod" not in existing:
        repo.create_head("prod")
    if "ed1" not in existing:
        repo.create_head("ed1")


def _repo() -> Repo:
    return Repo(SCRIPTS_REPO_PATH)


def commit_script(branch: str, script_id: int, content: str, message: str) -> str:
    """Write {script_id}.py to branch, commit, return commit hash."""
    repo = _repo()
    repo.heads[branch].checkout()
    path = SCRIPTS_REPO_PATH / f"{script_id}.py"
    path.write_text(content, encoding="utf-8")
    repo.index.add([f"{script_id}.py"])
    commit = repo.index.commit(message)
    return commit.hexsha


def get_script_content(branch: str, script_id: int) -> str:
    """Read {script_id}.py from branch without touching the worktree."""
    repo = _repo()
    try:
        blob = repo.heads[branch].commit.tree[f"{script_id}.py"]
        return blob.data_stream.read().decode("utf-8")
    except KeyError:
        raise FileNotFoundError(f"Script {script_id} not found on branch {branch!r}")


def list_scripts_on_branch(branch: str) -> list[str]:
    """Return list of .py filenames tracked on branch."""
    repo = _repo()
    return [
        item.path
        for item in repo.heads[branch].commit.tree.blobs
        if item.path.endswith(".py")
    ]


def merge_to_prod(script_id: int) -> None:
    """Copy {script_id}.py from ed1 to prod via a new commit."""
    content = get_script_content("ed1", script_id)
    commit_script("prod", script_id, content, f"merge script {script_id} from ed1")
