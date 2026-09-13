"""Reusable FastAPI dependencies: mock-auth current user + role guards."""
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.services.auth_service import resolve_token


def get_bearer_token(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def get_current_user(token: Optional[str] = Depends(get_bearer_token)) -> dict:
    user = resolve_token(token) if token else None
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")
    if user.get("status") == "suspended":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended.")
    return user


def get_optional_user(token: Optional[str] = Depends(get_bearer_token)) -> Optional[dict]:
    if not token:
        return None
    return resolve_token(token)


def require_role(*roles: str):
    def _dependency(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the following roles: {', '.join(roles)}.",
            )
        return user

    return _dependency
