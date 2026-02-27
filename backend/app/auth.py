import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

USERS = {
    "ed1": {"password": "1editor", "roles": ["viewer", "editor"]},
    "mo1": {"password": "2viewer", "roles": ["viewer"]},
}

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "dev-secret-key-change-in-prod")

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


class UserInfo(BaseModel):
    username: str
    roles: list[str]


@router.post("/login")
def login(body: LoginRequest, request: Request) -> UserInfo:
    user = USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    request.session["user"] = body.username
    return UserInfo(username=body.username, roles=user["roles"])


@router.post("/logout")
def logout(request: Request) -> dict:
    request.session.clear()
    return {"ok": True}


@router.get("/me")
def me(request: Request) -> UserInfo:
    username = request.session.get("user")
    if not username or username not in USERS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return UserInfo(username=username, roles=USERS[username]["roles"])


def _current_user(request: Request) -> UserInfo:
    username = request.session.get("user")
    if not username or username not in USERS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return UserInfo(username=username, roles=USERS[username]["roles"])


def require_viewer(user: Annotated[UserInfo, Depends(_current_user)]) -> UserInfo:
    if "viewer" not in user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewer role required")
    return user


def require_editor(user: Annotated[UserInfo, Depends(_current_user)]) -> UserInfo:
    if "editor" not in user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Editor role required")
    return user
