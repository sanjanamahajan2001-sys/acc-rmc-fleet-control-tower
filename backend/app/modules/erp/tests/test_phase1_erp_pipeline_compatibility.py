import pytest
import pytest_asyncio
import pathlib
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from app.core.config import settings
from app.modules.erp.parsers.context import CanonicalWorkbookContext
from app.modules.erp.parsers.csv_parser import CSVWorkbookParser
from app.modules.erp.validation.engine import CanonicalValidationEngine
from app.modules.erp.workers.persistence import PersistenceCoordinator


async def create_isolated_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, poolclass=NullPool, echo=False)
    session = AsyncSession(bind=engine, expire_on_commit=False)
    return session, engine


@pytest_asyncio.fixture(autouse=True)
async def cleanup_compat_records():
    yield
    session, engine = await create_isolated_session()
    async with session:
        await session.execute(text("DELETE FROM tbl_correlation_history WHERE dispatch_id IN (SELECT id FROM dispatches WHERE dispatch_number LIKE 'DISP-COMPAT-%')"))
        await session.execute(text("DELETE FROM trips WHERE dispatch_id IN (SELECT id FROM dispatches WHERE dispatch_number LIKE 'DISP-COMPAT-%')"))
        await session.execute(text("DELETE FROM dispatches WHERE dispatch_number LIKE 'DISP-COMPAT-%'"))
        await session.execute(text("DELETE FROM tickets WHERE ticket_number LIKE 'TCK-COMPAT-%'"))
        await session.execute(text("DELETE FROM orders WHERE customer_id IN (SELECT id FROM customers WHERE name LIKE 'COMPAT CUST %')"))
        await session.execute(text("DELETE FROM vehicles WHERE code LIKE 'V-VASCO-COMPAT-%'"))
        await session.execute(text("DELETE FROM sites WHERE original_address LIKE '%COMPAT%'"))
        await session.execute(text("DELETE FROM plants WHERE name LIKE 'ACC Test Vasco %'"))
        await session.execute(text("DELETE FROM customers WHERE name LIKE 'COMPAT CUST %'"))

        await session.commit()
    await engine.dispose()



@pytest.mark.asyncio
async def test_phase1_erp_pipeline_ingestion_compatibility(tmp_path):
    """Test full pipeline execution with active customer display override entity in DB."""
    uid = uuid.uuid4().hex[:6]
    plant_name = f"ACC Test Vasco {uid}"
    cust_name = f"COMPAT CUST {uid} COLVALE"
    disp_num = f"DISP-COMPAT-{uid}"
    tck_num = f"TCK-COMPAT-{uid}"
    veh_code = f"V-VASCO-COMPAT-{uid}"

    # 1. Create a dummy CSV file with isolated test plant
    csv_file = tmp_path / "test_ingest.csv"
    csv_content = (
        "plant_name,ticket_number,dispatch_number,dispatch_date,customer_name,vehicle_code,volume_m3\n"
        f"{plant_name},{tck_num},{disp_num},2026-08-21T10:00:00,{cust_name},{veh_code},8.0\n"
    )
    csv_file.write_text(csv_content)

    # 2. Setup workbook context & parse
    ctx = CanonicalWorkbookContext(
        import_job_id=f"job-{uuid.uuid4().hex[:6]}",
        workbook_name=csv_file.name,
        file_path=str(csv_file)
    )

    parser = CSVWorkbookParser()
    batches = []
    async for batch in parser.parse_workbook_batches(csv_file, batch_size=10):
        batches.append(batch)

    # 3. Validate & Map
    val_engine = CanonicalValidationEngine()
    persistable_batch, val_report, val_stats = await val_engine.validate_and_map_workbook(batches, ctx)

    session, engine = await create_isolated_session()
    async with session:
        counts = await PersistenceCoordinator.persist_batch(session, persistable_batch)
        await session.commit()
    await engine.dispose()

    assert counts["dispatches"] >= 1



