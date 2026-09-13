from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_bearer_token, get_current_user
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from app.services import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    if payload.role == "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin accounts cannot be self-registered.")
    try:
        user = auth_service.register_user(payload.name, payload.email, payload.password, payload.role, payload.phone)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    token = auth_service.issue_token(user["id"])
    return AuthResponse(token=token, user=UserPublic(**auth_service.public_user(user)))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    try:
        user = auth_service.authenticate(payload.email, payload.password)
    except auth_service.AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    token = auth_service.issue_token(user["id"])
    return AuthResponse(token=token, user=UserPublic(**auth_service.public_user(user)))


@router.post("/logout")
def logout(token: str | None = Depends(get_bearer_token)):
    if token:
        auth_service.revoke_token(token)
    return {"message": "Logged out."}


@router.get("/me", response_model=UserPublic)
def me(user: dict = Depends(get_current_user)):
    return UserPublic(**auth_service.public_user(user))
