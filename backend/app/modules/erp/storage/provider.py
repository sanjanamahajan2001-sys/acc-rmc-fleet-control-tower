"""
Storage Provider Interface Definition & Data Models
"""

import pathlib
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class BaseStorageProvider(ABC):
    """
    Abstract Base Storage Provider Interface for pluggable storage backends
    (e.g., Local Filesystem, AWS S3, Azure Blob Storage).
    """

    @abstractmethod
    async def init_storage(self) -> None:
        """Initialize storage container/directory structure."""

    @abstractmethod
    async def save_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> str:
        """Save a temporary chunk for a multi-part upload session."""

    @abstractmethod
    async def assemble_chunks(
        self, upload_id: str, total_chunks: int, target_relative_path: str
    ) -> str:
        """Assemble uploaded chunks into the final stored file."""

    @abstractmethod
    async def save_file(self, relative_path: str, data: bytes) -> str:
        """Save a complete file buffer directly to target relative path."""

    @abstractmethod
    async def get_file_path(self, relative_path: str) -> pathlib.Path:
        """Return the absolute Path reference for a stored file."""

    @abstractmethod
    def read_chunks(
        self, relative_path: str, chunk_size: int = 1048576
    ) -> AsyncGenerator[bytes, None]:
        """Stream stored file contents in chunks for hashing or verification."""

    @abstractmethod
    async def file_exists(self, relative_path: str) -> bool:
        """Check if a file exists at the given relative path."""

    @abstractmethod
    async def delete_file(self, relative_path: str) -> bool:
        """Delete a stored file or chunk directory."""

    @abstractmethod
    async def cleanup_upload_session(self, upload_id: str) -> None:
        """Clean up temporary upload session files and chunks."""
