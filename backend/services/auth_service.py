from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from configs.settings import settings
from configs.logger import get_logger

logger = get_logger(__name__)

_BCRYPT_ROUNDS = 12


# ── Password helpers ──────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a plain-text password with bcrypt (works with bcrypt >=4, 5)."""
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain-text password against bcrypt hash."""
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT helpers ───────────────────────────────────────────────────────────────

def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: str, role: str) -> str:
    return _create_token(
        {"sub": user_id, "role": role, "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    return _create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ── Service functions ─────────────────────────────────────────────────────────

def register(db: Session, payload: RegisterRequest) -> UserResponse:
    if db.query(User).filter(User.email == payload.email).first():
        raise ValueError("Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise ValueError("Username already taken")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("user_registered", user_id=user.id, username=user.username)
    return UserResponse.model_validate(user)


def login(db: Session, email: str, password: str) -> TokenResponse:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise ValueError("Invalid email or password")
    if not user.is_active:
        raise PermissionError("Account is disabled")

    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id)

    user.refresh_token = refresh_token
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    logger.info("user_logged_in", user_id=user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def refresh_access_token(db: Session, refresh_token: str) -> str:
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise ValueError("Invalid or expired refresh token")

    if payload.get("type") != "refresh":
        raise ValueError("Not a refresh token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.refresh_token != refresh_token:
        raise ValueError("Refresh token revoked or not found")
    if not user.is_active:
        raise PermissionError("Account is disabled")

    return create_access_token(user.id, user.role)


def logout(db: Session, user_id: str) -> None:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.refresh_token = None
        db.commit()
    logger.info("user_logged_out", user_id=user_id)


def get_user_by_id(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()
