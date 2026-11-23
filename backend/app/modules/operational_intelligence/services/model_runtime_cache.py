"""
WS-10 Phase 6.1 Model Runtime Cache & Management
Provides thread-safe in-memory caching of loaded MLModelVersion adapters with SHA-256 integrity verification.
Supports atomic invalidation and hot-reloading upon Phase 5 promotion/rollback events.
"""

import logging
import asyncio
from typing import Dict, Optional, Type
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.services.authoritative_resolver import AuthoritativeModelResolver
from app.modules.operational_intelligence.services.model_runtime_adapter import (
    ModelRuntimeAdapter,
    LightGBMRuntimeAdapter,
)

logger = logging.getLogger(__name__)


class ModelRuntimeCache:
    """
    In-memory singleton runtime cache for loaded ModelRuntimeAdapter instances.
    Provides SHA-256 verification on load and atomic cache invalidation/reloading.
    """

    _instance: Optional["ModelRuntimeCache"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self._adapters: Dict[str, ModelRuntimeAdapter] = {}

    @classmethod
    def get_instance(cls) -> "ModelRuntimeCache":
        if cls._instance is None:
            cls._instance = ModelRuntimeCache()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Resets the singleton instance (used for test isolation)."""
        cls._instance = None

    async def get_adapter(
        self,
        session: AsyncSession,
        model_family: str,
        adapter_cls: Type[ModelRuntimeAdapter] = LightGBMRuntimeAdapter,
    ) -> ModelRuntimeAdapter:
        """
        Retrieves the cached runtime adapter for a model family.
        If not cached, resolves the active PROMOTED model from DB, verifies SHA-256, loads adapter, and caches it.
        """
        async with self._lock:
            if model_family in self._adapters:
                return self._adapters[model_family]

            resolver = AuthoritativeModelResolver(session)
            model_ver = await resolver.resolve_authoritative_model(model_family)

            adapter = adapter_cls(
                model_name=model_ver.model_name,
                model_version=model_ver.model_version,
                artifact_path=model_ver.artifact_path,
                expected_sha256=model_ver.artifact_sha256,
            )

            self._adapters[model_family] = adapter
            logger.info(f"[RUNTIME CACHE] Cached adapter for '{model_family}' ({model_ver.model_version})")
            return adapter

    async def invalidate_cache(self, model_family: Optional[str] = None) -> None:
        """
        Invalidates cached runtime adapter for a specific family or all families.
        Call this when a promotion or rollback event occurs in Phase 5.
        """
        async with self._lock:
            if model_family:
                if model_family in self._adapters:
                    del self._adapters[model_family]
                    logger.info(f"[RUNTIME CACHE] Invalidated cache for family '{model_family}'")
            else:
                self._adapters.clear()
                logger.info("[RUNTIME CACHE] Invalidated entire runtime model cache")

    async def reload_adapter(
        self,
        session: AsyncSession,
        model_family: str,
        adapter_cls: Type[ModelRuntimeAdapter] = LightGBMRuntimeAdapter,
    ) -> ModelRuntimeAdapter:
        """Atomically invalidates and reloads the runtime adapter for a model family."""
        await self.invalidate_cache(model_family)
        return await self.get_adapter(session, model_family, adapter_cls)
