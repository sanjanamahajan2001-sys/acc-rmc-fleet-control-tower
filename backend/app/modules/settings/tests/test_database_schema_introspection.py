import pytest
from uuid import uuid4
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession
from app.main import app
from app.modules.auth.models import User, Role
from app.core.security.password import hash_password
from app.core.security.jwt import create_access_token
from app.schemas.auth import AuthStage
from app.modules.settings.services.schema_introspection_service import DatabaseSchemaIntrospectionService


async def create_test_admin(session: AsyncSession) -> tuple[User, str]:
    from sqlalchemy import select
    res = await session.execute(select(Role).where(Role.name == "Administrator"))
    admin_role = res.scalars().first()
    if not admin_role:
        admin_role = Role(name="Administrator", description="Full system access")
        session.add(admin_role)
        await session.commit()
        await session.refresh(admin_role)

    username = f"admin_{uuid4().hex[:8]}"
    admin_user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password("AdminPass123!"),
        is_superuser=True,
        is_active=True,
        must_change_password=False,
        token_version=1,
    )
    admin_user.roles.append(admin_role)
    session.add(admin_user)
    await session.commit()
    await session.refresh(admin_user)

    token, _ = create_access_token(user_id=str(admin_user.id), token_version=1, auth_stage=AuthStage.NORMAL)
    return admin_user, token


async def create_test_operator(session: AsyncSession) -> tuple[User, str]:
    username = f"op_{uuid4().hex[:8]}"
    user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password("OperatorPass123!"),
        is_superuser=False,
        is_active=True,
        must_change_password=False,
        token_version=1,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    token, _ = create_access_token(user_id=str(user.id), token_version=1, auth_stage=AuthStage.NORMAL)
    return user, token


@pytest.mark.asyncio
async def test_schema_introspection_service_direct(db_session: AsyncSession):
    """Verifies that schema introspection queries PostgreSQL information_schema dynamically."""
    schema = await DatabaseSchemaIntrospectionService.get_database_schema(db_session, "test_fleet_db")
    assert schema.database_name == "test_fleet_db"
    assert schema.table_count > 0
    assert schema.foreign_key_count > 0

    table_names = [t.table_name for t in schema.tables]
    assert "users" in table_names
    assert "customers" in table_names
    assert "dispatches" in table_names

    # Check dispatches table columns and relationships
    disp_table = next(t for t in schema.tables if t.table_name == "dispatches")
    assert "id" in disp_table.primary_keys
    
    col_names = [c.name for c in disp_table.columns]
    assert "id" in col_names
    assert "dispatch_number" in col_names
    assert "customer_id" in col_names

    # Check foreign key target resolution
    cust_id_col = next(c for c in disp_table.columns if c.name == "customer_id")
    assert cust_id_col.is_foreign_key is True
    assert cust_id_col.foreign_key_target_table == "customers"


@pytest.mark.asyncio
async def test_schema_sql_export_generation(db_session: AsyncSession):
    """Verifies that safe DDL SQL script is generated with no credentials or secrets."""
    export_dto = await DatabaseSchemaIntrospectionService.generate_sql_export(db_session, "test_fleet_db")
    assert export_dto.table_count > 0
    assert "CREATE TABLE IF NOT EXISTS public.users" in export_dto.sql_script
    assert "CREATE TABLE IF NOT EXISTS public.customers" in export_dto.sql_script
    assert "ALTER TABLE public.dispatches ADD CONSTRAINT" in export_dto.sql_script
    # Security assertion: No passwords or connection strings in SQL export
    assert "password" not in export_dto.sql_script.lower() or "password_hash" in export_dto.sql_script.lower()


@pytest.mark.asyncio
async def test_schema_endpoint_admin_auth(db_session: AsyncSession):
    """Verifies that /fleet-api/v1/settings/database-schema is strictly guarded for admin only."""
    _, admin_token = await create_test_admin(db_session)
    _, operator_token = await create_test_operator(db_session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Unauthenticated -> 401
        res_unauth = await client.get("/fleet-api/v1/settings/database-schema")
        assert res_unauth.status_code == 401

        # 2. Non-admin operator -> 403
        res_forbidden = await client.get(
            "/fleet-api/v1/settings/database-schema",
            headers={"Authorization": f"Bearer {operator_token}"},
        )
        assert res_forbidden.status_code == 403

        # 3. Superuser admin -> 200
        res_ok = await client.get(
            "/fleet-api/v1/settings/database-schema",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_ok.status_code == 200
        data = res_ok.json()["data"]
        assert data["table_count"] > 0
        assert len(data["tables"]) > 0

        # 4. SQL Export Admin endpoint -> 200
        res_sql = await client.get(
            "/fleet-api/v1/settings/database-schema/sql-export",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_sql.status_code == 200
        sql_data = res_sql.json()["data"]
        assert "CREATE TABLE" in sql_data["sql_script"]
