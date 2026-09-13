"""Mock authentication service (Section 18: safe mock auth for the MVP).

Passwords are hashed with passlib/bcrypt (never stored in plaintext).
Opaque bearer tokens are issued on register/login and stored in a JSON
file (app/data/tokens.json) mapping token -> user_id. GET /api/auth/me
resolves the bearer token back to a user record.
"""
from datetime import datetime, timedelta
from typing import Optional

import bcrypt

from app.models.user import AccountStatus, User, UserRole
from app.utils.json_store import tokens_store, users_store
from app.utils.validation import new_id, new_token

# Passwords are hashed with bcrypt directly (never stored in plaintext).
# bcrypt truncates input at 72 bytes; that limit is acceptable for MVP mock auth.


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except Exception:
        return False


class AuthError(Exception):
    pass


def get_user_by_email(email: str) -> Optional[dict]:
    return users_store.find_one(lambda u: u.get("email", "").lower() == email.lower())


def register_user(name: str, email: str, password: str, role: UserRole, phone: Optional[str] = None) -> dict:
    if get_user_by_email(email):
        raise AuthError("An account with this email already exists.")
    user_id = new_id("u_")
    record = {
        "id": user_id,
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "role": role.value if isinstance(role, UserRole) else role,
        "phone": phone,
        "status": AccountStatus.active.value,
        "created_at": datetime.utcnow().isoformat(),
        "restaurant_id": None,
        "rider_online": False,
        "rider_approved": True,
        "favorites_restaurants": [],
        "favorites_meals": [],
    }
    users_store.create(record)
    return record


def authenticate(email: str, password: str) -> dict:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise AuthError("Invalid email or password.")
    if user.get("status") == AccountStatus.suspended.value:
        raise AuthError("This account has been suspended.")
    return user


def issue_token(user_id: str) -> str:
    token = new_token()
    tokens_store.create({
        "token": token,
        "user_id": user_id,
        "issued_at": datetime.utcnow().isoformat(),
        "revoked": False,
    })
    return token


def resolve_token(token: str) -> Optional[dict]:
    if not token:
        return None
    record = tokens_store.find_one(lambda t: t.get("token") == token and not t.get("revoked"))
    if not record:
        return None
    return users_store.get(record["user_id"])


def revoke_token(token: str) -> None:
    record = tokens_store.find_one(lambda t: t.get("token") == token)
    if record:
        tokens_store.update(record["token"], {"revoked": True}, id_field="token")


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
        "phone": user.get("phone"),
        "status": user.get("status", "active"),
        "restaurant_id": user.get("restaurant_id"),
    }
