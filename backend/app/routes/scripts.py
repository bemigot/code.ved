import ast
from math import floor
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import UserInfo, require_editor, require_viewer
from ..db import get_session
from ..git_store import commit_script, get_script_content, merge_to_prod
from ..models import Execution, Script, ScriptVersion

router = APIRouter(prefix="/api/scripts")

SessionDep = Annotated[Session, Depends(get_session)]


# ── Response schemas ──────────────────────────────────────────────────────────

class VersionInfo(BaseModel):
    id: int
    major: int
    minor: int
    committer: str
    created_at: str
    git_commit_hash: str
    parent_script_id: Optional[int]
    parent_version_id: Optional[int]


class ScriptSummary(BaseModel):
    id: int
    ordering_number: float
    descriptive_name: str
    major: int
    minor: int
    last_run_at: Optional[str]
    last_run_exit_code: Optional[int]


class ScriptDetail(BaseModel):
    id: int
    ordering_number: float
    descriptive_name: str
    content: str
    version: VersionInfo
    last_execution: Optional[dict]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_name(content: str) -> str:
    """Return first non-empty line of module docstring, or 'Untitled'."""
    try:
        tree = ast.parse(content)
        docstring = ast.get_docstring(tree)
        if docstring:
            for line in docstring.splitlines():
                line = line.strip()
                if line:
                    return line
    except SyntaxError:
        pass
    return "Untitled"


def _latest_version(script_id: int, session: Session) -> Optional[ScriptVersion]:
    stmt = (
        select(ScriptVersion)
        .where(ScriptVersion.script_id == script_id)
        .order_by(ScriptVersion.id.desc())  # type: ignore[arg-type]
    )
    return session.exec(stmt).first()


def _last_execution(version_id: int, session: Session) -> Optional[Execution]:
    stmt = (
        select(Execution)
        .where(Execution.script_version_id == version_id)
        .order_by(Execution.id.desc())  # type: ignore[arg-type]
    )
    return session.exec(stmt).first()


def _next_ordering_number(session: Session) -> float:
    stmt = select(Script).where(Script.is_deleted == False)  # noqa: E712
    scripts = session.exec(stmt).all()
    if not scripts:
        return 1.0
    return float(max(floor(s.ordering_number) for s in scripts) + 1)


def _get_script_or_404(script_id: int, session: Session) -> Script:
    script = session.get(Script, script_id)
    if not script or script.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found")
    return script


def _to_version_info(v: ScriptVersion) -> VersionInfo:
    return VersionInfo(
        id=v.id,  # type: ignore[arg-type]
        major=v.major,
        minor=v.minor,
        committer=v.committer,
        created_at=v.created_at.isoformat(),
        git_commit_hash=v.git_commit_hash,
        parent_script_id=v.parent_script_id,
        parent_version_id=v.parent_version_id,
    )


def _exe_to_dict(exe: Execution) -> dict:
    return {
        "id": exe.id,
        "exit_code": exe.exit_code,
        "stdout": exe.stdout,
        "stderr": exe.stderr,
        "started_at": exe.started_at.isoformat(),
        "finished_at": exe.finished_at.isoformat() if exe.finished_at else None,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("")
def list_scripts(
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_viewer)],
) -> list[ScriptSummary]:
    stmt = select(Script).where(Script.is_deleted == False)  # noqa: E712
    scripts = session.exec(stmt).all()
    result = []
    for script in scripts:
        ver = _latest_version(script.id, session)  # type: ignore[arg-type]
        if not ver:
            continue
        try:
            content = get_script_content("ed1", script.id)  # type: ignore[arg-type]
            name = _parse_name(content)
        except FileNotFoundError:
            name = "Untitled"
        exe = _last_execution(ver.id, session)  # type: ignore[arg-type]
        result.append(
            ScriptSummary(
                id=script.id,  # type: ignore[arg-type]
                ordering_number=script.ordering_number,
                descriptive_name=name,
                major=ver.major,
                minor=ver.minor,
                last_run_at=exe.finished_at.isoformat() if exe and exe.finished_at else None,
                last_run_exit_code=exe.exit_code if exe else None,
            )
        )
    result.sort(key=lambda s: s.ordering_number)
    return result


@router.get("/{script_id}")
def get_script(
    script_id: int,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_viewer)],
) -> ScriptDetail:
    script = _get_script_or_404(script_id, session)
    ver = _latest_version(script.id, session)  # type: ignore[arg-type]
    if not ver:
        raise HTTPException(status_code=500, detail="Script has no versions")
    content = get_script_content("ed1", script.id)  # type: ignore[arg-type]
    exe = _last_execution(ver.id, session)  # type: ignore[arg-type]
    return ScriptDetail(
        id=script.id,  # type: ignore[arg-type]
        ordering_number=script.ordering_number,
        descriptive_name=_parse_name(content),
        content=content,
        version=_to_version_info(ver),
        last_execution=_exe_to_dict(exe) if exe else None,
    )


class CreateScriptBody(BaseModel):
    content: str = ""


@router.post("", status_code=status.HTTP_201_CREATED)
def create_script(
    body: CreateScriptBody,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> ScriptDetail:
    ordering_number = _next_ordering_number(session)
    script = Script(ordering_number=ordering_number)
    session.add(script)
    session.commit()
    session.refresh(script)

    git_hash = commit_script("ed1", script.id, body.content, f"create script {script.id}")  # type: ignore[arg-type]
    ver = ScriptVersion(
        script_id=script.id,
        major=0,
        minor=1,
        git_commit_hash=git_hash,
        committer=user.username,
    )
    session.add(ver)
    session.commit()
    session.refresh(ver)

    return ScriptDetail(
        id=script.id,  # type: ignore[arg-type]
        ordering_number=script.ordering_number,
        descriptive_name=_parse_name(body.content),
        content=body.content,
        version=_to_version_info(ver),
        last_execution=None,
    )


class SaveScriptBody(BaseModel):
    content: str


@router.put("/{script_id}")
def save_script(
    script_id: int,
    body: SaveScriptBody,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> ScriptDetail:
    script = _get_script_or_404(script_id, session)
    latest = _latest_version(script.id, session)  # type: ignore[arg-type]
    if not latest:
        raise HTTPException(status_code=500, detail="Script has no versions")

    new_minor = latest.minor + 1
    git_hash = commit_script(
        "ed1", script.id, body.content,  # type: ignore[arg-type]
        f"save script {script.id} v{latest.major}.{new_minor}",
    )
    ver = ScriptVersion(
        script_id=script.id,
        major=latest.major,
        minor=new_minor,
        git_commit_hash=git_hash,
        committer=user.username,
    )
    session.add(ver)
    session.commit()
    session.refresh(ver)

    return ScriptDetail(
        id=script.id,  # type: ignore[arg-type]
        ordering_number=script.ordering_number,
        descriptive_name=_parse_name(body.content),
        content=body.content,
        version=_to_version_info(ver),
        last_execution=None,
    )


@router.post("/{script_id}/fork", status_code=status.HTTP_201_CREATED)
def fork_script(
    script_id: int,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> ScriptDetail:
    source = _get_script_or_404(script_id, session)
    source_ver = _latest_version(source.id, session)  # type: ignore[arg-type]
    if not source_ver:
        raise HTTPException(status_code=500, detail="Source script has no versions")
    content = get_script_content("ed1", source.id)  # type: ignore[arg-type]

    ordering_number = _next_ordering_number(session)
    new_script = Script(ordering_number=ordering_number)
    session.add(new_script)
    session.commit()
    session.refresh(new_script)

    git_hash = commit_script(
        "ed1", new_script.id, content,  # type: ignore[arg-type]
        f"fork script {new_script.id} from {source.id}",
    )
    ver = ScriptVersion(
        script_id=new_script.id,
        major=0,
        minor=1,
        git_commit_hash=git_hash,
        committer=user.username,
        parent_script_id=source.id,
        parent_version_id=source_ver.id,
    )
    session.add(ver)
    session.commit()
    session.refresh(ver)

    return ScriptDetail(
        id=new_script.id,  # type: ignore[arg-type]
        ordering_number=new_script.ordering_number,
        descriptive_name=_parse_name(content),
        content=content,
        version=_to_version_info(ver),
        last_execution=None,
    )


@router.post("/{script_id}/bump-major")
def bump_major(
    script_id: int,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> ScriptDetail:
    script = _get_script_or_404(script_id, session)
    latest = _latest_version(script.id, session)  # type: ignore[arg-type]
    if not latest:
        raise HTTPException(status_code=500, detail="Script has no versions")

    ver = ScriptVersion(
        script_id=script.id,
        major=latest.major + 1,
        minor=0,
        git_commit_hash=latest.git_commit_hash,
        committer=user.username,
    )
    session.add(ver)
    session.commit()
    session.refresh(ver)

    content = get_script_content("ed1", script.id)  # type: ignore[arg-type]
    return ScriptDetail(
        id=script.id,  # type: ignore[arg-type]
        ordering_number=script.ordering_number,
        descriptive_name=_parse_name(content),
        content=content,
        version=_to_version_info(ver),
        last_execution=None,
    )


@router.post("/{script_id}/merge")
def merge_script(
    script_id: int,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> dict:
    _get_script_or_404(script_id, session)
    merge_to_prod(script_id)
    return {"ok": True}


@router.get("/{script_id}/versions")
def list_versions(
    script_id: int,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_viewer)],
) -> list[VersionInfo]:
    _get_script_or_404(script_id, session)
    stmt = (
        select(ScriptVersion)
        .where(ScriptVersion.script_id == script_id)
        .order_by(ScriptVersion.id.desc())  # type: ignore[arg-type]
    )
    versions = session.exec(stmt).all()
    return [_to_version_info(v) for v in versions]
