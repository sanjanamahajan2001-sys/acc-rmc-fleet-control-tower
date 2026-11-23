"""
ERP Async Repositories for Canonical & Metadata Entities
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.erp.models import (
    Customer,
    Dispatch,
    Driver,
    ImportJob,
    Invoice,
    Material,
    Order,
    Plant,
    Product,
    Route,
    Site,
    Ticket,
    Trip,
    Vehicle,
)
from app.repositories.base import GenericRepository


class PlantRepository(GenericRepository[Plant]):
    """Async repository for Plant canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Plant, session)

    async def get_by_code(self, code: str) -> Plant | None:
        stmt = select(Plant).where(Plant.code == code, Plant.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalars().first()


class SiteRepository(GenericRepository[Site]):
    """Async repository for Site canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Site, session)


class CustomerRepository(GenericRepository[Customer]):
    """Async repository for Customer canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Customer, session)

    async def get_by_code(self, code: str) -> Customer | None:
        stmt = select(Customer).where(
            Customer.code == code, Customer.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class MaterialRepository(GenericRepository[Material]):
    """Async repository for Material canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Material, session)


class ProductRepository(GenericRepository[Product]):
    """Async repository for Product canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Product, session)


class VehicleRepository(GenericRepository[Vehicle]):
    """Async repository for Vehicle canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Vehicle, session)


class DriverRepository(GenericRepository[Driver]):
    """Async repository for Driver canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Driver, session)


class RouteRepository(GenericRepository[Route]):
    """Async repository for Route canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Route, session)


class OrderRepository(GenericRepository[Order]):
    """Async repository for Order canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Order, session)


class TicketRepository(GenericRepository[Ticket]):
    """Async repository for Ticket canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Ticket, session)


class DispatchRepository(GenericRepository[Dispatch]):
    """Async repository for Dispatch canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Dispatch, session)

    async def get_by_dispatch_number(self, dispatch_number: str) -> Dispatch | None:
        stmt = select(Dispatch).where(
            Dispatch.dispatch_number == dispatch_number, Dispatch.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class InvoiceRepository(GenericRepository[Invoice]):
    """Async repository for Invoice canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Invoice, session)


class TripRepository(GenericRepository[Trip]):
    """Async repository for Trip canonical entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Trip, session)


class ImportJobRepository(GenericRepository[ImportJob]):
    """Async repository for ImportJob metadata entity."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ImportJob, session)

    async def get_by_job_number(self, job_number: str) -> ImportJob | None:
        stmt = select(ImportJob).where(
            ImportJob.job_number == job_number, ImportJob.is_deleted.is_(False)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
