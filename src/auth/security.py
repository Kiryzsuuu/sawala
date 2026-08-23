"""Password hashing and JWT issuing/verification."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from src.utils.env import JWT_EXPIRE_MINUTES, JWT_SECRET

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _pwd_context.verify(password, password_hash)


def create_access_token(user_id: str, email: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)
