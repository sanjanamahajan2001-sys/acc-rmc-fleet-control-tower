"""
Authentication DTO Schemas
Workstream X.2 Production Schemas
"""

import datetime
from app.schemas.auth import AuthStage


from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, EmailStr, ConfigDict

AccessLevel = Literal["none", "view", "edit"]

PLATFORM_SECTIONS: list[str] = [
    "platform_home",
    "site_dashboard",
    "overall_dashboard",
    "dispatch_analysis",
    "dispatch_optimization",
    "operational_intelligence",
    "predictive_intelligence",
    "control_tower_actions",
    "alerts",
    "reports",
    "erp_import",
    "erp_explorer",
    "settings",
    "user_management",
]

PLATFORM_SECTION_LABELS: dict[str, str] = {
    "platform_home": "Platform Home",
    "site_dashboard": "Site Dashboard",
    "overall_dashboard": "Overall Dashboard",
    "dispatch_analysis": "Dispatch Analysis",
    "dispatch_optimization": "Dispatch Optimization",
    "operational_intelligence": "Operational Intelligence",
    "predictive_intelligence": "Predictive Intelligence",
    "control_tower_actions": "Control Tower Actions",
    "alerts": "Alert Center",
    "reports": "Reports & Exports",
    "erp_import": "ERP Import",
    "erp_explorer": "ERP Data Explorer",
    "settings": "Settings Center",
    "user_management": "User Management",
}


def get_full_admin_permissions() -> dict[str, str]:
    """Returns edit permissions across all canonical platform sections."""
    return {section: "edit" for section in PLATFORM_SECTIONS}


TESTED_PILOT_SECTIONS: list[str] = [
    "platform_home",
    "site_dashboard",
    "overall_dashboard",
    "dispatch_analysis",
    "alerts",
    "reports",
    "erp_explorer",
]


def get_default_operator_permissions() -> dict[str, str]:
    """
    Returns safe default permissions for regular operators:
    View-only for tested pilot operational telemetry, and none for unmapped/complex or administrative areas.
    """
    perms = {section: "none" for section in PLATFORM_SECTIONS}
    for sec in TESTED_PILOT_SECTIONS:
        perms[sec] = "view"
    return perms



def resolve_user_section_permissions(
    is_superuser: bool,
    stored_perms: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    """
    Resolves the canonical section permissions for a user.
    - Superusers always receive full edit access across all sections.
    - Non-superusers receive their explicit permissions, falling back to safe operator defaults for missing sections.
    - Enforces valid access levels: 'none', 'view', 'edit'.
    """
    if is_superuser:
        return get_full_admin_permissions()

    resolved = get_default_operator_permissions()
    if stored_perms and isinstance(stored_perms, dict):
        for section in PLATFORM_SECTIONS:
            if section in stored_perms:
                val = str(stored_perms[section]).strip().lower()
                if val in ("none", "view", "edit"):
                    resolved[section] = val

    return resolved


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, description="Username or Email")
    password: str = Field(..., min_length=6, description="Plaintext password")
    remember_me: bool = Field(default=False, description="Remember me cookie extension")


class UserPreferenceDTO(BaseModel):
    theme: str = "dark"
    default_dashboard: str = "operational_overview"
    last_plant_code: Optional[str] = None
    timezone: str = "UTC"
    rows_per_page: int = 20
    collapsed_sidebar: bool = False
    ui_settings: dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class UserDTO(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    must_change_password: bool = False
    auth_stage: str = "NORMAL"
    roles: list[str] = []
    section_permissions: dict[str, str] = Field(default_factory=dict)
    preferences: Optional[UserPreferenceDTO] = None
    last_login_at: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)


class LoginResponseDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    auth_stage: str = "NORMAL"
    user: UserDTO


class SessionResponseDTO(BaseModel):
    authenticated: bool
    user: Optional[UserDTO] = None


class ChangePasswordRequestDTO(BaseModel):
    new_password: str = Field(..., min_length=8, description="New strong password")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")


class PlantScopeDTO(BaseModel):
    id: str
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class AdminUserDetailDTO(UserDTO):
    is_password_temporary: bool = False
    password_changed_at: Optional[datetime.datetime] = None
    deleted_at: Optional[datetime.datetime] = None
    deleted_by: Optional[str] = None
    plant_scopes: list[PlantScopeDTO] = []

    model_config = ConfigDict(from_attributes=True)


class AdminUserCreateRequestDTO(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(...)
    full_name: Optional[str] = Field(default=None, max_length=128)
    role_ids: list[str] = Field(default_factory=list)
    plant_ids: list[str] = Field(default_factory=list)
    section_permissions: Optional[dict[str, str]] = Field(default=None)


class AdminUserCreateResponseDTO(BaseModel):
    user: AdminUserDetailDTO
    temporary_password: str = Field(description="One-time cryptographically generated temporary password")


class AdminUserUpdateRequestDTO(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[list[str]] = None
    plant_ids: Optional[list[str]] = None
    section_permissions: Optional[dict[str, str]] = None



class UserListResponseDTO(BaseModel):
    items: list[AdminUserDetailDTO]
    total: int
    page: int
    size: int
    pages: int


