import tempfile
from datetime import datetime
from pathlib import Path

import docker
import docker.errors
from sqlmodel import Session

from ..db import engine
from ..models import Execution

IMAGE = "python:3.14-slim"
INTERPRETER = "cpython-3.14"
TIMEOUT_SECONDS = 30


def run_script(
    script_id: int,
    version_id: int,
    content: str,
    test_data: str,
) -> Execution:
    """Execute script in Docker, persist result, return Execution row."""
    started_at = datetime.utcnow()
    exit_code = -1
    stdout = ""
    stderr = ""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "script.py").write_text(content, encoding="utf-8")
        (tmppath / "input").write_text(test_data, encoding="utf-8")

        try:
            client = docker.from_env()
            container = client.containers.run(
                image=IMAGE,
                command=["python", "/runner/script.py", "/runner/input"],
                volumes={str(tmppath): {"bind": "/runner", "mode": "ro"}},
                network_mode="none",
                mem_limit="256m",
                nano_cpus=500_000_000,  # 0.5 CPUs
                detach=True,
                remove=False,
            )
            try:
                result = container.wait(timeout=TIMEOUT_SECONDS)
                exit_code = result["StatusCode"]
                stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            except Exception:
                exit_code = -1
                stderr = f"Execution timed out after {TIMEOUT_SECONDS} seconds"
            finally:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
        except docker.errors.DockerException as exc:
            exit_code = -1
            stderr = f"Docker error: {exc}"

    finished_at = datetime.utcnow()
    exe = Execution(
        script_version_id=version_id,
        started_at=started_at,
        finished_at=finished_at,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        interpreter=INTERPRETER,
    )
    with Session(engine) as session:
        session.add(exe)
        session.commit()
        session.refresh(exe)
    return exe
