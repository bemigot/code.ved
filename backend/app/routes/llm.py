import os
import time
from typing import Annotated, Optional

import openai
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session

from ..auth import UserInfo, require_editor
from ..db import get_session
from ..models import LLMInteraction

router = APIRouter(prefix="/api/llm")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
USE_LLM = os.getenv("USE_LLM", "openrouter/free")

STOP_WORDS = [
    "rm -rf",
    "os.system",
    "os.popen",
    "__import__",
    "shutil.rmtree",
    "subprocess.call",
    "subprocess.run",
    "subprocess.Popen",
]

SYSTEM_PROMPT = (
    "You are a Python scripting assistant. "
    "Help the user write, debug, and improve Python scripts. "
    "Provide clear, correct Python code. "
    "Do not suggest operations that could harm the host system."
)

_client: Optional[openai.AsyncOpenAI] = None


def _get_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
    return _client


SessionDep = Annotated[Session, Depends(get_session)]


class CompleteRequest(BaseModel):
    script_id: Optional[int] = None
    script_version_id: Optional[int] = None
    prompt: str
    context_code: str = ""


class CompleteResponse(BaseModel):
    response_text: str
    model_id: str
    cost_usd: float


@router.post("/complete")
async def llm_complete(
    body: CompleteRequest,
    session: SessionDep,
    user: Annotated[UserInfo, Depends(require_editor)],
) -> CompleteResponse:
    # Guardrail: stop-word filter
    lowered = body.prompt.lower()
    for word in STOP_WORDS:
        if word.lower() in lowered:
            interaction = LLMInteraction(
                script_version_id=body.script_version_id,
                prompt=body.prompt,
                response=f"[REJECTED: stop-word '{word}' detected]",
                model_id="none",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
            )
            session.add(interaction)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Prompt contains disallowed content: '{word}'",
            )

    # Build messages
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if body.context_code:
        messages.append({
            "role": "user",
            "content": f"Here is the current script:\n```python\n{body.context_code}\n```",
        })
        messages.append({
            "role": "assistant",
            "content": "I can see the script. How can I help?",
        })
    messages.append({"role": "user", "content": body.prompt})

    started = time.monotonic()
    try:
        completion = await _get_client().chat.completions.create(
            model=USE_LLM,
            messages=messages,
        )
    except openai.OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"LLM error: {exc}",
        )
    latency_ms = int((time.monotonic() - started) * 1000)

    response_text = completion.choices[0].message.content or ""
    model_id = completion.model or USE_LLM
    input_tokens = completion.usage.prompt_tokens if completion.usage else 0
    output_tokens = completion.usage.completion_tokens if completion.usage else 0
    # OpenRouter may include total_cost in usage; fall back to 0.0
    cost_usd = float(getattr(completion.usage, "total_cost", None) or 0.0)

    interaction = LLMInteraction(
        script_version_id=body.script_version_id,
        prompt=body.prompt,
        response=response_text,
        model_id=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )
    session.add(interaction)
    session.commit()

    return CompleteResponse(
        response_text=response_text,
        model_id=model_id,
        cost_usd=cost_usd,
    )
