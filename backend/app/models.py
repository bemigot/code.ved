from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Script(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ordering_number: float
    is_deleted: bool = False


class ScriptVersion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    script_id: int = Field(foreign_key="script.id")
    major: int
    minor: int
    git_commit_hash: str
    committer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    parent_script_id: Optional[int] = None
    parent_version_id: Optional[int] = None


class Execution(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    script_version_id: int = Field(foreign_key="scriptversion.id")
    started_at: datetime
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    interpreter: str


class LLMInteraction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    script_version_id: Optional[int] = Field(default=None, foreign_key="scriptversion.id")
    prompt: str
    response: str
    model_id: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
