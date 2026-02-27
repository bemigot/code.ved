from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import create_db_and_tables
from .git_store import init_repo


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    init_repo()
    yield


app = FastAPI(lifespan=lifespan)
