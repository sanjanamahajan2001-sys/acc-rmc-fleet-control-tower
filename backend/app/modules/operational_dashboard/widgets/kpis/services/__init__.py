from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.modules.operational_dashboard.widgets.kpis.dtos import KPICardItemDTO


class BaseKPIEngine(ABC):
    """Abstract Base Class for isolated WS-03.1 KPI Calculation Engines."""

    @abstractmethod
    def calculate(self, observations: Any) -> KPICardItemDTO:
        """Calculates KPI DTO from raw repository observations."""
        pass
