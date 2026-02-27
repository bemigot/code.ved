from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from .auth import SESSION_SECRET_KEY, router as auth_router
from .db import create_db_and_tables
from .git_store import init_repo
from .routes.execution import router as execution_router
from .routes.llm import router as llm_router
from .routes.scripts import router as scripts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    init_repo()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY, session_cookie="ved_session")

app.include_router(auth_router)
app.include_router(scripts_router)
app.include_router(execution_router)
app.include_router(llm_router)
