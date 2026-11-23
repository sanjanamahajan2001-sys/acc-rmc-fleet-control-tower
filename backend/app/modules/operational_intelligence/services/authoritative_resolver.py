"""
WS-10 Phase 6.1 Authoritative Model Resolver
Resolves exactly 1 active PROMOTED production model per certified model family from PostgreSQL.
Fails closed if 0 or >1 PROMOTED models exist for a family.
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_registry import MLModelVersion

logger = logging.getLogger(__name__)

SUPPORTED_MODEL_FAMILIES = [
    "delay_regressor",
    "turnaround_regressor",
    "sla_breach_classifier",
    "plant_risk_classifier",
]

class NoPromotedModelError(Exception):
    """Raised when 0 PROMOTED models exist for a required model family."""
    pass

class AmbiguousModelAuthorityError(Exception):
    """Raised when >1 PROMOTED models exist for a single model family."""
    pass

class UnknownModelFamilyError(Exception):
    """Raised when an unknown model family is requested."""
    pass


class AuthoritativeModelResolver:
    """
    Deterministically resolves the single authoritative PROMOTED model version
    for each certified production model family.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def resolve_authoritative_model(self, model_family: str) -> MLModelVersion:
        """
        Resolves the single active PROMOTED model version for a given family.
        Enforces strict single authority: raises exception if 0 or >1 PROMOTED models exist.
        """
        if model_family not in SUPPORTED_MODEL_FAMILIES:
            raise UnknownModelFamilyError(f"Model family '{model_family}' is not supported. Must be one of {SUPPORTED_MODEL_FAMILIES}")

        stmt = select(MLModelVersion).where(
            MLModelVersion.model_name == model_family,
            MLModelVersion.lifecycle_status == "PROMOTED",
            MLModelVersion.is_deleted == False,
        )

        res = await self.session.execute(stmt)
        models = res.scalars().all()

        if not models:
            logger.error(f"[AUTHORITATIVE RESOLVER] 0 PROMOTED models found for family '{model_family}'")
            raise NoPromotedModelError(f"No active PROMOTED model version found for family '{model_family}'")

        if len(models) > 1:
            versions = [m.model_version for m in models]
            logger.critical(f"[AUTHORITATIVE RESOLVER] Ambiguous model authority for family '{model_family}': multiple active versions {versions}")
            raise AmbiguousModelAuthorityError(f"Multiple active PROMOTED model versions found for family '{model_family}': {versions}")

        authoritative_model = models[0]
        logger.info(f"[AUTHORITATIVE RESOLVER] Resolved {model_family} -> {authoritative_model.model_version} (id={authoritative_model.id})")
        return authoritative_model

    async def resolve_all_authoritative_models(self) -> Dict[str, MLModelVersion]:
        """
        Resolves active PROMOTED models across all four certified model families.
        Returns dictionary mapping model_family -> MLModelVersion.
        """
        result = {}
        for family in SUPPORTED_MODEL_FAMILIES:
            result[family] = await self.resolve_authoritative_model(family)
        return result
