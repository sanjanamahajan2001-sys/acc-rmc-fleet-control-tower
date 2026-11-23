"""
TM Details Service Layer
Workstream 2.6 Service
"""

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.site_dashboard.widgets.tm_details.repository import TMDetailsRepository
from app.modules.site_dashboard.widgets.tm_details.calculations import TMDetailsCalculations
from app.modules.site_dashboard.widgets.tm_details.dtos import TMDetailRowDTO, TMDetailsResponseDTO


class TMDetailsService:
    """Orchestrates SQL fetches and duration calculations for TM Details."""

    @staticmethod
    async def get_tm_details(
        session: AsyncSession,
        filters: dict[str, Any],
        page: int = 1,
        page_size: int = 20,
    ) -> TMDetailsResponseDTO:
        raw_rows, total_count = await TMDetailsRepository.get_filtered_dispatches(session, filters, page, page_size)

        items: list[TMDetailRowDTO] = []
        for r in raw_rows:
            parsed = TMDetailsCalculations.classify_dispatch(r)
            items.append(TMDetailRowDTO(**parsed))

        return TMDetailsResponseDTO(
            total_count=total_count,
            page=page,
            page_size=page_size,
            items=items,
        )
