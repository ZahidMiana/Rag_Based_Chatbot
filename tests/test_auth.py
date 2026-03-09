"""
tests/test_auth.py
Unit tests for Module 5: Authentication & User Management
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from jose import jwt
from configs.settings import settings


# ── Schema validation tests ───────────────────────────────────────────────────

from backend.schemas.auth import RegisterRequest, TokenResponse, UserResponse


def test_register_request_valid():
    req = RegisterRequest(username="zahid_01", email="zahid@example.com", password="secret123")
    assert req.username == "zahid_01"


def test_register_request_username_normalized():
    req = RegisterRequest(username="ZAHID", email="z@example.com", password="secret123")
    assert req.username == "zahid"


def test_register_request_short_password():
    with pytest.raises(Exception):
        RegisterRequest(username="user1", email="u@example.com", password="short")


def test_register_request_short_username():
    with pytest.raises(Exception):
        RegisterRequest(username="ab", email="u@example.com", password="password123")


def test_register_request_invalid_username_chars():
    with pytest.raises(Exception):
        RegisterRequest(username="user name!", email="u@example.com", password="password123")


def test_token_response_default_type():
    t = TokenResponse(access_token="aaa", refresh_token="bbb")
    assert t.token_type == "bearer"


# ── Password hashing tests ────────────────────────────────────────────────────

from backend.services.auth_service import hash_password, verify_password


def test_password_hash_not_plain():
    hashed = hash_password("mypassword")
    assert hashed != "mypassword"


def test_password_verify_correct():
    hashed = hash_password("correct_password")
    assert verify_password("correct_password", hashed) is True


def test_password_verify_wrong():
    hashed = hash_password("correct_password")
    assert verify_password("wrong_password", hashed) is False


# ── JWT token tests ───────────────────────────────────────────────────────────

from backend.services.auth_service import (
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_access_token_payload():
    token = create_access_token("user-123", "user")
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "user"
    assert payload["type"] == "access"


def test_refresh_token_payload():
    token = create_refresh_token("user-456")
    payload = decode_token(token)
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_decode_invalid_token_raises():
    with pytest.raises(Exception):
        decode_token("not.a.valid.token")


def test_decode_tampered_token_raises():
    token = create_access_token("user-1", "user")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(Exception):
        decode_token(tampered)


# ── auth_service register tests ───────────────────────────────────────────────

from backend.services import auth_service


def _mock_db_no_existing_user():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.add = MagicMock()
    db.commit = MagicMock()

    def refresh_side_effect(user):
        user.id = "new-uuid"
        user.created_at = datetime.now(timezone.utc)
        user.is_active = True
        user.role = "user"

    db.refresh = MagicMock(side_effect=refresh_side_effect)
    return db


def test_register_success():
    db = _mock_db_no_existing_user()
    payload = RegisterRequest(username="newuser", email="new@example.com", password="password123")
    result = auth_service.register(db, payload)
    assert result.username == "newuser"
    assert db.add.called


def test_register_duplicate_email():
    db = MagicMock()
    existing = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = existing

    payload = RegisterRequest(username="user1", email="taken@example.com", password="password123")
    with pytest.raises(ValueError, match="Email already registered"):
        auth_service.register(db, payload)


def test_register_duplicate_username():
    db = MagicMock()
    # First call (email check) returns None, second (username check) returns existing
    db.query.return_value.filter.return_value.first.side_effect = [None, MagicMock()]

    payload = RegisterRequest(username="taken", email="new@example.com", password="password123")
    with pytest.raises(ValueError, match="Username already taken"):
        auth_service.register(db, payload)


# ── auth_service login tests ──────────────────────────────────────────────────

def test_login_success():
    mock_user = MagicMock()
    mock_user.id = "uid-1"
    mock_user.role = "user"
    mock_user.is_active = True
    mock_user.hashed_password = hash_password("validpass")

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_user

    result = auth_service.login(db, "user@example.com", "validpass")
    assert result.access_token
    assert result.refresh_token
    assert result.token_type == "bearer"


def test_login_wrong_password():
    mock_user = MagicMock()
    mock_user.hashed_password = hash_password("correct")
    mock_user.is_active = True

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_user

    with pytest.raises(ValueError, match="Invalid email or password"):
        auth_service.login(db, "user@example.com", "wrong")


def test_login_user_not_found():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(ValueError, match="Invalid email or password"):
        auth_service.login(db, "ghost@example.com", "password")


def test_login_disabled_account():
    mock_user = MagicMock()
    mock_user.hashed_password = hash_password("pass")
    mock_user.is_active = False

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_user

    with pytest.raises(PermissionError, match="Account is disabled"):
        auth_service.login(db, "user@example.com", "pass")


# ── refresh token tests ───────────────────────────────────────────────────────

def test_refresh_access_token_success():
    refresh_tok = create_refresh_token("uid-99")

    mock_user = MagicMock()
    mock_user.id = "uid-99"
    mock_user.role = "user"
    mock_user.is_active = True
    mock_user.refresh_token = refresh_tok

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_user

    new_token = auth_service.refresh_access_token(db, refresh_tok)
    payload = decode_token(new_token)
    assert payload["sub"] == "uid-99"
    assert payload["type"] == "access"


def test_refresh_with_access_token_fails():
    access_tok = create_access_token("uid-1", "user")
    db = MagicMock()
    with pytest.raises(ValueError):
        auth_service.refresh_access_token(db, access_tok)


def test_refresh_revoked_token_fails():
    refresh_tok = create_refresh_token("uid-2")

    mock_user = MagicMock()
    mock_user.refresh_token = "different_token"
    mock_user.is_active = True

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_user

    with pytest.raises(ValueError, match="Refresh token revoked"):
        auth_service.refresh_access_token(db, refresh_tok)


# ── logout test ───────────────────────────────────────────────────────────────

def test_logout_clears_refresh_token():
    mock_user = MagicMock()
    mock_user.refresh_token = "some_token"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = mock_user

    auth_service.logout(db, "uid-1")
    assert mock_user.refresh_token is None
    db.commit.assert_called_once()
