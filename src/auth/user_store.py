"""User accounts and password-reset tokens, stored in MongoDB (separate
from the SQLite session/snapshot data in src/data/database.py, which stays
SQLite - this only holds login-related data)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection

from src.utils.env import MONGODB_DB_NAME, MONGODB_URI
from src.utils.logger import get_logger

logger = get_logger(__name__)


class UserStore:
    def __init__(self, uri: str = MONGODB_URI, db_name: str = MONGODB_DB_NAME):
        self._client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self._db = self._client[db_name]
        self.users: Collection = self._db["users"]
        self.reset_tokens: Collection = self._db["password_reset_tokens"]
        self.users.create_index("email", unique=True)
        self.reset_tokens.create_index("token", unique=True)
        logger.info("Connected to MongoDB (%s/%s)", uri.split("@")[-1], db_name)

    def ping(self) -> bool:
        try:
            self._client.admin.command("ping")
            return True
        except Exception as exc:
            logger.error("MongoDB ping failed: %s", exc)
            return False

    def create_user(self, email: str, password_hash: str) -> dict[str, Any]:
        doc = {
            "email": email.lower(),
            "password_hash": password_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = self.users.insert_one(doc)
        doc["_id"] = result.inserted_id
        return doc

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return self.users.find_one({"email": email.lower()})

    def get_user_by_id(self, user_id) -> dict[str, Any] | None:
        from bson import ObjectId
        return self.users.find_one({"_id": ObjectId(user_id)})

    def count_users(self) -> int:
        return self.users.count_documents({})

    def update_password(self, user_id, password_hash: str) -> None:
        from bson import ObjectId
        self.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"password_hash": password_hash}})

    def create_reset_token(self, token: str, user_id, expires_at: str) -> None:
        self.reset_tokens.insert_one({
            "token": token,
            "user_id": str(user_id),
            "expires_at": expires_at,
            "used": False,
        })

    def get_reset_token(self, token: str) -> dict[str, Any] | None:
        return self.reset_tokens.find_one({"token": token})

    def mark_reset_token_used(self, token: str) -> None:
        self.reset_tokens.update_one({"token": token}, {"$set": {"used": True}})

    def close(self) -> None:
        self._client.close()


def bootstrap_super_admin(store: "UserStore", email: str, password: str) -> None:
    """Ensures the configured super-admin account (ADMIN_EMAIL in .env)
    exists with the super_admin role. Doesn't touch its password if the
    account already exists, so a password changed later isn't clobbered
    back to the .env default on every restart."""
    from src.auth.security import hash_password

    existing = store.get_user_by_email(email)
    if existing:
        if existing.get("role") != "super_admin":
            store.users.update_one({"_id": existing["_id"]}, {"$set": {"role": "super_admin"}})
            logger.info("Upgraded %s to super_admin", email)
        return

    doc = store.create_user(email, hash_password(password))
    store.users.update_one({"_id": doc["_id"]}, {"$set": {"role": "super_admin"}})
    logger.info("Created initial super_admin account: %s", email)
