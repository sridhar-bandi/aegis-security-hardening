"""Unit tests for RBAC utilities (no DB required)."""
import pytest
from jose import jwt

from aegis.services.rbac import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from aegis.config import settings


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"

    def test_verify_correct_password(self):
        hashed = hash_password("correct")
        assert verify_password("correct", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_two_hashes_differ(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        # bcrypt uses random salt — hashes should differ
        assert h1 != h2


class TestJWT:
    def test_create_and_decode_token(self):
        token = create_access_token("user-123", "admin")
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_token_contains_expiry(self):
        token = create_access_token("u", "user")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert "exp" in payload

    def test_tampered_token_rejected(self):
        from fastapi import HTTPException
        token = create_access_token("user-abc", "user")
        # Corrupt the signature
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".invalidsignature"
        with pytest.raises(HTTPException):
            decode_token(tampered)
