"""
Phase 1 Master Verification Suite: Database Schema & Migration Foundation
Verifies ORM alignment, migration defaults, existing user data preservation, and plant scope table structures.
"""

import pytest
from uuid import uuid4
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User, user_plant_scopes
from app.modules.erp.models import Plant


@pytest.mark.asyncio
async def test_phase1_schema_fields_exist(session: AsyncSession):
    """Verify Phase 1 columns exist on the User ORM model."""
    assert hasattr(User, "must_change_password")
    assert hasattr(User, "is_password_temporary")
    assert hasattr(User, "password_changed_at")
    assert hasattr(User, "token_version")
    assert hasattr(User, "deleted_at")
    assert hasattr(User, "deleted_by")


@pytest.mark.asyncio
async def test_phase1_user_defaults(session: AsyncSession):
    """Verify Phase 1 default values on newly instantiated User model."""
    user = User(
        username=f"test_user_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash="argon2id_hash_sample"
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.must_change_password is False
    assert user.is_password_temporary is False
    assert user.password_changed_at is None
    assert user.token_version == 1
    assert user.deleted_at is None
    assert user.deleted_by is None


@pytest.mark.asyncio
async def test_phase1_existing_users_preserved(session: AsyncSession):
    """Verify existing admin user in DB maintains safe backward-compatible defaults."""
    stmt = select(User).where(User.username == "admin")
    user = (await session.execute(stmt)).scalars().first()

    if user:
        assert user.must_change_password is False
        assert user.is_password_temporary is False
        assert user.token_version == 1
        assert user.deleted_at is None
        assert user.deleted_by is None


@pytest.mark.asyncio
async def test_phase1_token_version_default(session: AsyncSession):
    """Verify token_version is strictly initialized to 1."""
    user = User(
        username=f"tv_user_{uuid4().hex[:8]}",
        email=f"tv_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash="argon2id_hash_sample"
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.token_version == 1


@pytest.mark.asyncio
async def test_phase1_password_lifecycle_defaults(session: AsyncSession):
    """Verify password lifecycle flags default to False and password_changed_at is NULL."""
    user = User(
        username=f"pass_user_{uuid4().hex[:8]}",
        email=f"pass_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash="argon2id_hash_sample"
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.must_change_password is False
    assert user.is_password_temporary is False
    assert user.password_changed_at is None


@pytest.mark.asyncio
async def test_phase1_soft_delete_fields(session: AsyncSession):
    """Verify soft-delete fields can be updated cleanly without hard deletion."""
    admin_stmt = select(User).where(User.username == "admin")
    admin = (await session.execute(admin_stmt)).scalars().first()
    admin_id = admin.id if admin else None

    user = User(
        username=f"sd_user_{uuid4().hex[:8]}",
        email=f"sd_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash="argon2id_hash_sample"
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)

    # Soft deactivate
    user.is_active = False
    user.deleted_at = user.created_at
    user.deleted_by = admin_id
    await session.commit()

    # Re-query
    stmt = select(User).where(User.id == user.id)
    reloaded = (await session.execute(stmt)).scalars().first()
    assert reloaded.is_active is False
    assert reloaded.deleted_at is not None
    if admin_id:
        assert reloaded.deleted_by == admin_id


@pytest.mark.asyncio
async def test_phase1_plant_scope_schema(session: AsyncSession):
    """Verify normalized user_plant_scopes table schema and ORM relationship."""
    user = User(
        username=f"plant_user_{uuid4().hex[:8]}",
        email=f"plant_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash="argon2id_hash_sample"
    )
    session.add(user)
    await session.commit()

    # Fetch any plant from DB
    plant_stmt = select(Plant)
    plant = (await session.execute(plant_stmt)).scalars().first()

    if plant:
        await session.execute(
            text("INSERT INTO user_plant_scopes (user_id, plant_id) VALUES (:u, :p)"),
            {"u": user.id, "p": plant.id}
        )
        await session.commit()

        # Query user_plant_scopes
        res = await session.execute(
            text("SELECT user_id, plant_id FROM user_plant_scopes WHERE user_id = :u"),
            {"u": user.id}
        )
        scopes = res.fetchall()
        assert len(scopes) == 1
        assert scopes[0][1] == plant.id


@pytest.mark.asyncio
async def test_phase1_orm_database_alignment(session: AsyncSession):
    """Verify ORM model columns map 1-to-1 to database information schema columns."""
    res = await session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'users';
    """))
    db_cols = {row[0]: row for row in res.fetchall()}

    assert "must_change_password" in db_cols
    assert db_cols["must_change_password"][2] == "NO"
    assert db_cols["must_change_password"][3] == "false"

    assert "is_password_temporary" in db_cols
    assert db_cols["is_password_temporary"][2] == "NO"
    assert db_cols["is_password_temporary"][3] == "false"

    assert "token_version" in db_cols
    assert db_cols["token_version"][2] == "NO"
    assert db_cols["token_version"][3] == "1"

    assert "password_changed_at" in db_cols
    assert db_cols["password_changed_at"][2] == "YES"

    assert "deleted_at" in db_cols
    assert db_cols["deleted_at"][2] == "YES"

    assert "deleted_by" in db_cols
    assert db_cols["deleted_by"][2] == "YES"
