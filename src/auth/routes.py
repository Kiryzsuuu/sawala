"""Login, password reset, and super-admin user management endpoints."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from src.auth.dependencies import make_get_current_user, make_require_super_admin
from src.auth.email import send_password_reset_email
from src.auth.security import (
    create_access_token,
    generate_reset_token,
    hash_password,
    verify_password,
)
from src.utils.env import PUBLIC_URL
from src.utils.logger import get_logger

logger = get_logger(__name__)

RESET_TOKEN_TTL_HOURS = 1
VALID_ROLES = {"admin", "super_admin"}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "admin"


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    password: str | None = None
    role: str | None = None


def _public_user(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user.get("role", "admin"),
        "created_at": user.get("created_at"),
    }


def register_auth_routes(app, user_store):
    get_current_user = make_get_current_user(user_store)
    require_super_admin = make_require_super_admin(get_current_user)

    auth_router = APIRouter(prefix="/api/auth", tags=["auth"])
    admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

    @auth_router.post("/login")
    def login(body: LoginRequest):
        user = user_store.get_user_by_email(body.email)
        if not user or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Email atau password salah")

        token = create_access_token(str(user["_id"]), user["email"])
        return {"access_token": token, "user": _public_user(user)}

    @auth_router.get("/me")
    def me(user: dict = Depends(get_current_user)):
        return _public_user(user)

    @auth_router.post("/forgot-password")
    def forgot_password(body: ForgotPasswordRequest):
        user = user_store.get_user_by_email(body.email)
        if user:
            token = generate_reset_token()
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_TTL_HOURS)).isoformat()
            user_store.create_reset_token(token, user["_id"], expires_at)
            reset_link = f"{PUBLIC_URL}/reset-password?token={token}"
            send_password_reset_email(user["email"], reset_link)
        # Selalu balas sukses walau email tidak ditemukan, supaya endpoint ini
        # tidak bisa dipakai untuk mengecek email mana saja yang terdaftar.
        return {"status": "ok", "message": "Kalau email terdaftar, link reset sudah dikirim"}

    @auth_router.post("/reset-password")
    def reset_password(body: ResetPasswordRequest):
        record = user_store.get_reset_token(body.token)
        if not record or record.get("used"):
            raise HTTPException(400, "Token reset tidak valid atau sudah dipakai")

        expires_at = datetime.fromisoformat(record["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(400, "Token reset sudah kedaluwarsa")

        user_store.update_password(record["user_id"], hash_password(body.new_password))
        user_store.mark_reset_token_used(body.token)
        return {"status": "ok"}

    @admin_router.get("/users")
    def list_users(_: dict = Depends(require_super_admin)):
        return {"users": [_public_user(u) for u in user_store.users.find()]}

    @admin_router.post("/users")
    def create_user(body: CreateUserRequest, _: dict = Depends(require_super_admin)):
        if body.role not in VALID_ROLES:
            raise HTTPException(400, f"role harus salah satu dari {sorted(VALID_ROLES)}")
        if user_store.get_user_by_email(body.email):
            raise HTTPException(409, "Email sudah terdaftar")

        doc = user_store.create_user(body.email, hash_password(body.password))
        user_store.users.update_one({"_id": doc["_id"]}, {"$set": {"role": body.role}})
        doc["role"] = body.role
        return _public_user(doc)

    @admin_router.patch("/users/{user_id}")
    def update_user(user_id: str, body: UpdateUserRequest, current: dict = Depends(require_super_admin)):
        try:
            target = user_store.get_user_by_id(user_id)
        except InvalidId:
            raise HTTPException(404, "User tidak ditemukan")
        if not target:
            raise HTTPException(404, "User tidak ditemukan")

        updates: dict = {}
        if body.email is not None:
            existing = user_store.get_user_by_email(body.email)
            if existing and str(existing["_id"]) != user_id:
                raise HTTPException(409, "Email sudah dipakai user lain")
            updates["email"] = body.email.lower()
        if body.password is not None:
            updates["password_hash"] = hash_password(body.password)
        if body.role is not None:
            if body.role not in VALID_ROLES:
                raise HTTPException(400, f"role harus salah satu dari {sorted(VALID_ROLES)}")
            if str(target["_id"]) == str(current["_id"]) and body.role != "super_admin":
                raise HTTPException(400, "Tidak bisa menurunkan role akun sendiri")
            updates["role"] = body.role

        if updates:
            user_store.users.update_one({"_id": target["_id"]}, {"$set": updates})
            target = user_store.get_user_by_id(user_id)
        return _public_user(target)

    @admin_router.delete("/users/{user_id}")
    def delete_user(user_id: str, current: dict = Depends(require_super_admin)):
        if user_id == str(current["_id"]):
            raise HTTPException(400, "Tidak bisa menghapus akun sendiri")
        try:
            target = user_store.get_user_by_id(user_id)
        except InvalidId:
            raise HTTPException(404, "User tidak ditemukan")
        if not target:
            raise HTTPException(404, "User tidak ditemukan")

        user_store.users.delete_one({"_id": target["_id"]})
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(admin_router)

    return get_current_user
