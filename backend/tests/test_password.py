"""
Unit tests for Argon2id Password Hashing Subsystem
"""

import pytest

from app.core.security.password import hash_password, verify_password


def test_password_hash_generation():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert "$argon2id$" in hashed


def test_password_verification_success():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True


def test_password_verification_failure():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert verify_password("WrongPassword123!", hashed) is False


def test_empty_password_handling():
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")

    assert verify_password("", "some_hash") is False
    assert verify_password("some_pass", "") is False
