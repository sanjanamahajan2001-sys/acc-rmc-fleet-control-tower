import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.core.exceptions import AuthorizationForbiddenError
from app.dependencies.auth import require_section_permission
from app.modules.auth.models import User, UserPreference, Role
from app.schemas.auth import TokenPayload

@pytest.mark.asyncio
async def test_superuser_universal_bypass():
    guard = require_section_permission("erp_import", "edit")
    claims = TokenPayload(
        sub=str(uuid.uuid4()),
        jti=str(uuid.uuid4()),
        exp=9999999999,
        iat=1000000000,
        type="access",
        auth_stage="NORMAL",
        token_version=1,
    )

    mock_user = MagicMock(spec=User)
    mock_user.is_superuser = True
    mock_user.is_active = True
    mock_user.deleted_at = None
    mock_user.roles = []

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute.return_value = mock_result

    result = await guard(claims=claims, session=mock_session)
    assert result == claims


@pytest.mark.asyncio
async def test_admin_role_universal_bypass():
    guard = require_section_permission("settings", "edit")
    claims = TokenPayload(
        sub=str(uuid.uuid4()),
        jti=str(uuid.uuid4()),
        exp=9999999999,
        iat=1000000000,
        type="access",
        auth_stage="NORMAL",
        token_version=1,
    )

    admin_role = MagicMock(spec=Role)
    admin_role.name = "Administrator"

    mock_user = MagicMock(spec=User)
    mock_user.is_superuser = False
    mock_user.is_active = True
    mock_user.deleted_at = None
    mock_user.roles = [admin_role]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute.return_value = mock_result

    result = await guard(claims=claims, session=mock_session)
    assert result == claims


@pytest.mark.asyncio
async def test_view_only_user_rejected_on_edit_requirement():
    guard = require_section_permission("erp_import", "edit")
    claims = TokenPayload(
        sub=str(uuid.uuid4()),
        jti=str(uuid.uuid4()),
        exp=9999999999,
        iat=1000000000,
        type="access",
        auth_stage="NORMAL",
        token_version=1,
    )

    mock_pref = MagicMock(spec=UserPreference)
    mock_pref.ui_settings = {
        "section_permissions": {
            "erp_import": "view"
        }
    }

    mock_user = MagicMock(spec=User)
    mock_user.is_superuser = False
    mock_user.is_active = True
    mock_user.deleted_at = None
    mock_user.roles = []
    mock_user.preferences = mock_pref

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute.return_value = mock_result

    with pytest.raises(AuthorizationForbiddenError) as exc_info:
        await guard(claims=claims, session=mock_session)

    assert "Write access denied" in str(exc_info.value) or "view-only" in str(exc_info.value)


@pytest.mark.asyncio
async def test_explicit_edit_permission_accepted():
    guard = require_section_permission("control_tower_actions", "edit")
    claims = TokenPayload(
        sub=str(uuid.uuid4()),
        jti=str(uuid.uuid4()),
        exp=9999999999,
        iat=1000000000,
        type="access",
        auth_stage="NORMAL",
        token_version=1,
    )

    mock_pref = MagicMock(spec=UserPreference)
    mock_pref.ui_settings = {
        "section_permissions": {
            "control_tower_actions": "edit"
        }
    }

    mock_user = MagicMock(spec=User)
    mock_user.is_superuser = False
    mock_user.is_active = True
    mock_user.deleted_at = None
    mock_user.roles = []
    mock_user.preferences = mock_pref

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = mock_user
    mock_session.execute.return_value = mock_result

    result = await guard(claims=claims, session=mock_session)
    assert result == claims
