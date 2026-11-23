"""
Argon2id Password Hashing Subsystem

Provides production-grade password hashing and verification using Argon2id.
Enforces timing-safe verification and enterprise security parameters.
"""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

# Enterprise Argon2id Hasher Configuration
# time_cost=3, memory_cost=65536 (64MB), parallelism=4
_argon2_hasher = Argon2Hasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
)

_password_hash = PasswordHash((_argon2_hasher,))


def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using Argon2id.
    Raises ValueError if password is empty or invalid.
    """
    if not password:
        raise ValueError("Password cannot be empty")
    return _password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against an Argon2id hashed password string.
    Returns True if valid, False otherwise. Timing-safe execution.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        res = _password_hash.verify(plain_password, hashed_password)
        if not res:
            from app.core.logging import get_logger
            get_logger("auth.verify_password").warning(
                f"[PASSWORD VERIFY FAIL] plain='{plain_password}' (len={len(plain_password)}) vs hash='{hashed_password[:30]}...'"
            )
        return res
    except Exception as exc:
        from app.core.logging import get_logger
        get_logger("auth.verify_password").error(
            f"[PASSWORD VERIFY EXCEPTION]: {exc}", exc_info=True
        )
        return False

