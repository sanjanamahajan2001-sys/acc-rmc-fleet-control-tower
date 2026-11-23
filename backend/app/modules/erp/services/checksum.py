"""
SHA-256 Checksum Generation & File Integrity Verification Service
"""

import hashlib
from collections.abc import AsyncGenerator

from app.modules.erp.storage.provider import BaseStorageProvider


class ChecksumService:
    """
    Computes streaming SHA-256 file hashes and performs binary integrity verification.
    """

    def __init__(self, storage_provider: BaseStorageProvider):
        self.storage_provider = storage_provider

    async def compute_hash_from_stream(
        self, stream: AsyncGenerator[bytes, None]
    ) -> str:
        """Compute SHA-256 checksum dynamically from an async chunk stream."""
        hasher = hashlib.sha256()
        async for chunk in stream:
            hasher.update(chunk)
        return hasher.hexdigest()

    async def compute_file_hash(self, relative_path: str) -> str:
        """Compute SHA-256 checksum for a stored file using streaming chunks."""
        stream = self.storage_provider.read_chunks(relative_path)
        return await self.compute_hash_from_stream(stream)

    async def verify_file_integrity(
        self, relative_path: str, expected_sha256: str
    ) -> bool:
        """Verify that a stored file matches the expected SHA-256 hash."""
        actual_hash = await self.compute_file_hash(relative_path)
        return actual_hash.lower() == expected_sha256.lower()

    @staticmethod
    def compute_bytes_sha256(data: bytes) -> str:
        """Compute SHA-256 checksum for an in-memory byte buffer."""
        return hashlib.sha256(data).hexdigest()
