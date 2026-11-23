"""
Security Core Init
"""

from app.core.security.audit import log_security_event
from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_and_validate_token,
)
from app.core.security.middleware import AuthenticationMiddleware
from app.core.security.password import hash_password, verify_password
from app.core.security.revocation import (
    InMemoryTokenRevocationStore,
    TokenRevocationStore,
    revocation_store,
)

__all__ = [
    "AuthenticationMiddleware",
    "InMemoryTokenRevocationStore",
    "TokenRevocationStore",
    "create_access_token",
    "create_refresh_token",
    "decode_and_validate_token",
    "hash_password",
    "log_security_event",
    "revocation_store",
    "verify_password",
]
