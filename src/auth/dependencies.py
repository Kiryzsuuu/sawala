"""FastAPI dependencies for authenticated / role-gated routes.

Built as factories (make_get_current_user(user_store)) instead of module-
level singletons because the UserStore instance is created at app startup
(needs the DB connection), matching the pattern already used for `engine`
elsewhere in this app.
"""
from __future__ import annotations

from typing import Callable

from fastapi import Depends, Header, HTTPException

from src.auth.security import decode_access_token


def make_get_current_user(user_store) -> Callable[..., dict]:
    def get_current_user(authorization: str | None = Header(default=None)) -> dict:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Belum login")

        token = authorization.removeprefix("Bearer ").strip()
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(401, "Sesi login tidak valid atau kedaluwarsa")

        user = user_store.get_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(401, "Akun tidak ditemukan")

        return user

    return get_current_user


def make_require_super_admin(get_current_user: Callable[..., dict]) -> Callable[..., dict]:
    def require_super_admin(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") != "super_admin":
            raise HTTPException(403, "Hanya super admin yang bisa mengakses ini")
        return user

    return require_super_admin
