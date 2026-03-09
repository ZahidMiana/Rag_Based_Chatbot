from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from db.database import get_db
from backend.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from backend.services import auth_service
from backend.middleware.auth_middleware import get_current_user
from backend.middleware.rate_limit import limiter
from backend.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.register(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        return auth_service.login(db, payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        new_access = auth_service.refresh_access_token(db, payload.refresh_token)
        return TokenResponse(access_token=new_access, refresh_token=payload.refresh_token)
    except (ValueError, PermissionError) as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auth_service.logout(db, current_user.id)
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user
