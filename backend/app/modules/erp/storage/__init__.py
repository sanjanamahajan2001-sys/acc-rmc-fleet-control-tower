"""
WS1.2 Storage Package Module Exports
"""

from app.modules.erp.storage.factory import get_storage_provider
from app.modules.erp.storage.local import LocalStorageProvider
from app.modules.erp.storage.provider import BaseStorageProvider

__all__ = [
    "BaseStorageProvider",
    "LocalStorageProvider",
    "get_storage_provider",
]
