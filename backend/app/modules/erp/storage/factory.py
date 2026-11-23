"""
Storage Provider Factory Definition
Supports dynamic selection of storage backends (Local Filesystem, S3, Azure Blob) based on application configuration.
"""

import pathlib

from app.core.config import settings
from app.core.exceptions import DomainValidationError
from app.modules.erp.storage.local import LocalStorageProvider
from app.modules.erp.storage.provider import BaseStorageProvider


def get_storage_provider(
    provider_type: str | None = None,
    root_dir: str | pathlib.Path | None = None,
) -> BaseStorageProvider:
    """
    Factory function instantiating the requested or configured BaseStorageProvider.
    """
    selected_type = (provider_type or settings.STORAGE_PROVIDER).upper()
    target_dir = root_dir or settings.STORAGE_ROOT_DIR

    if selected_type == "LOCAL":
        return LocalStorageProvider(root_dir=target_dir)
    elif selected_type in ("S3", "AWS"):
        raise NotImplementedError(
            "S3StorageProvider will be registered when AWS S3 storage is enabled."
        )
    elif selected_type in ("AZURE", "BLOB"):
        raise NotImplementedError(
            "AzureBlobStorageProvider will be registered when Azure Blob storage is enabled."
        )
    else:
        raise DomainValidationError(
            f"Unsupported storage provider type: '{selected_type}'"
        )
