import asyncio
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, select

from ..auth import UserInfo, require_editor, require_viewer
from ..db import get_session
from ..executor.docker_runner import run_script
from ..executor.grouper import group_scripts
from ..git_store import get_script_content
from ..models import Execution, Script, ScriptVersion

router = APIRouter(prefix="/api/execute")

SessionDep = Annotated[Session, Depends(get_session)]


# ── Schemas ────────────────────────────────────────────────────────────────────

class RunBody(BaseModel):
    test_data: str = ""


class ExecutionResult(BaseModel):
    id: int
    script_version_id: int
    exit_code: Optional[int]
    stdout: str
    stderr: str
    started_at: str
    finished_at: Optional[str]
    interpreter: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _latest_version(script_id: int, session: Session) -> Optional[ScriptVersion]:
    stmt = (
        select(ScriptVersion)
        .where(ScriptVersion.script_id == script_id)
        .order_by(ScriptVersion.id.desc())  # type: ignore[arg-type]
    )
    return session.exec(stmt).first()


def _exe_to_result(exe: Execution) -> ExecutionResult:
    return ExecutionResult(
        id=exe.id,  # type: ignore[arg-type]
        script_version_id=exe.script_version_id,
        exit_code=exe.exit_code,
        stdout=exe.stdout,
        stderr=exe.stderr,
        started_at=exe.started_at.isoformat(),
        finished_at=exe.finished_at.isoformat() if exe.finished_at else None,
        interpreter=exe.interpreter,
    )


# ── Routes ─────────────────────────────────────────────────────────────────────

# NOTE: /all must be defined before /{script_id} so the literal path wins.

@router.post("/all")
async def execute_all(
    body: RunBody,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> list[ExecutionResult]:
    """Run every script on the prod branch, grouped by floor(ordering_number)."""
    stmt = select(Script).where(Script.is_deleted == False)  # noqa: E712
    scripts = list(session.exec(stmt).all())

    # Resolve version + content in the main thread before spawning threads.
    grouped_tasks: list[list[tuple[int, int, str]]] = []
    for group in group_scripts(scripts):
        tasks: list[tuple[int, int, str]] = []
        for script in group:
            ver = _latest_version(int(script.id), session)  # type: ignore[arg-type]
            if not ver:
                continue
            try:
                content = get_script_content("prod", int(script.id))  # type: ignore[arg-type]
            except FileNotFoundError:
                continue
            tasks.append((int(script.id), int(ver.id), content))  # type: ignore[arg-type]
        if tasks:
            grouped_tasks.append(tasks)

    results: list[ExecutionResult] = []
    for group in grouped_tasks:
        exes = await asyncio.gather(*[
            asyncio.to_thread(run_script, sid, vid, cnt, body.test_data)
            for sid, vid, cnt in group
        ])
        results.extend(_exe_to_result(exe) for exe in exes)

    return results


@router.post("/{script_id}")
async def execute_script(
    script_id: int,
    body: RunBody,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> ExecutionResult:
    """Run a single script from the prod branch."""
    script = session.get(Script, script_id)
    if not script or script.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script not found")

    ver = _latest_version(script_id, session)
    if not ver:
        raise HTTPException(status_code=500, detail="Script has no versions")

    try:
        content = get_script_content("prod", script_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Script not on prod branch — merge first",
        )

    exe = await asyncio.to_thread(run_script, script_id, int(ver.id), content, body.test_data)  # type: ignore[arg-type]
    return _exe_to_result(exe)


@router.get("/{script_id}/last")
def last_execution(
    script_id: int,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_viewer)],
) -> Optional[ExecutionResult]:
    """Return the most recent execution for any version of this script."""
    stmt = select(ScriptVersion.id).where(ScriptVersion.script_id == script_id)
    version_ids = list(session.exec(stmt).all())
    if not version_ids:
        return None

    exe_stmt = (
        select(Execution)
        .where(Execution.script_version_id.in_(version_ids))  # type: ignore[union-attr]
        .order_by(Execution.id.desc())  # type: ignore[arg-type]
    )
    exe = session.exec(exe_stmt).first()
    return _exe_to_result(exe) if exe else None
