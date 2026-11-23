"""
Unit tests for Dual-Token JWT Engine
"""

import uuid

import pytest

from app.core.exceptions import ExpiredTokenError, InvalidTokenError
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_and_validate_token,
)


def test_create_and_validate_access_token():
    user_id = str(uuid.uuid4())
    token, jti = create_access_token(user_id=user_id, tenant_id="T1")

    payload = decode_and_validate_token(token, expected_type="access")
    assert payload.sub == user_id
    assert payload.jti == jti
    assert payload.type == "access"
    assert payload.tenant_id == "T1"


def test_create_and_validate_refresh_token():
    user_id = str(uuid.uuid4())
    token, jti = create_refresh_token(user_id=user_id)

    payload = decode_and_validate_token(token, expected_type="refresh")
    assert payload.sub == user_id
    assert payload.jti == jti
    assert payload.type == "refresh"


def test_expired_token_rejection():
    user_id = str(uuid.uuid4())
    token, _ = create_access_token(user_id=user_id, expires_delta_seconds=-10)

    with pytest.raises(ExpiredTokenError, match="Token has expired"):
        decode_and_validate_token(token)


def test_invalid_signature_rejection():
    user_id = str(uuid.uuid4())
    token, _ = create_access_token(user_id=user_id)
    tampered_token = token[:-5] + "XXXXX"

    with pytest.raises(InvalidTokenError):
        decode_and_validate_token(tampered_token)


def test_wrong_token_type_rejection():
    user_id = str(uuid.uuid4())
    token, _ = create_access_token(user_id=user_id)

    with pytest.raises(InvalidTokenError, match="Invalid token type"):
        decode_and_validate_token(token, expected_type="refresh")
