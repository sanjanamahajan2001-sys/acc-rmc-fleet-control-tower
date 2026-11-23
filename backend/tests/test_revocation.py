"""
Unit tests for Token Revocation & JTI Blacklist Store
"""

import pytest

from app.core.security.revocation import InMemoryTokenRevocationStore


@pytest.mark.asyncio
async def test_token_revocation_store():
    store = InMemoryTokenRevocationStore()
    jti = "test-jti-12345"

    assert await store.is_jti_revoked(jti) is False

    await store.revoke_jti(jti, expires_in_seconds=3600)
    assert await store.is_jti_revoked(jti) is True


@pytest.mark.asyncio
async def test_duplicate_token_revocation():
    store = InMemoryTokenRevocationStore()
    jti = "test-jti-67890"

    await store.revoke_jti(jti, expires_in_seconds=3600)
    await store.revoke_jti(jti, expires_in_seconds=3600)
    assert await store.is_jti_revoked(jti) is True
