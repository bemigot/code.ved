"""LLM connectivity checker — uses the same env vars as app/routes/llm.py."""
import asyncio
import os

import openai
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
USE_LLM = os.getenv("USE_LLM", "openrouter/free")


async def main() -> None:
    if not OPENROUTER_API_KEY:
        print("ERROR: OPENROUTER_API_KEY is not set")
        return

    print(f"Model : {USE_LLM}")
    print("Sending test prompt...")

    client = openai.AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    try:
        completion = await client.chat.completions.create(
            model=USE_LLM,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Write a Python hello world script. "
                        "Return bare Python code only — no comments, no backticks, no markdown."
                    ),
                }
            ],
        )
    except openai.OpenAIError as exc:
        print(f"ERROR: {exc}")
        return

    print("OK\n")
    print(completion.choices[0].message.content)


asyncio.run(main())
