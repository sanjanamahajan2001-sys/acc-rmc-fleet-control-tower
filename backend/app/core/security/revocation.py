"""
Token Revocation & JTI Blacklist Store Abstraction

Provides abstract interface (TokenRevocationStore) and in-memory/Redis-compatible
implementation for revoking JWT JTIs to enforce single-use refresh token rotation and logout.
"""

from abc import ABC, abstractmethod


class TokenRevocationStore(ABC):
    """
    Abstract Token Revocation Store Interface.
    Decouples business logic from specific backing store (Redis/In-Memory).
    """

    @abstractmethod
    async def revoke_jti(self, jti: str, expires_in_seconds: int) -> None:
        """Revokes a JWT ID (JTI)."""

    @abstractmethod
    async def is_jti_revoked(self, jti: str) -> bool:
        """Returns True if JTI is in revocation store, False otherwise."""


class InMemoryTokenRevocationStore(TokenRevocationStore):
    """
    In-Memory implementation of TokenRevocationStore for testing and single-node deployment.
    Redis implementation will subclass TokenRevocationStore in future infrastructure modules.
    """

    def __init__(self) -> None:
        self._revoked_jtis: set[str] = set()

    async def revoke_jti(self, jti: str, expires_in_seconds: int) -> None:
        self._revoked_jtis.add(jti)

    async def is_jti_revoked(self, jti: str) -> bool:
        return jti in self._revoked_jtis


# Platform global token revocation store instance
revocation_store: TokenRevocationStore = InMemoryTokenRevocationStore()
