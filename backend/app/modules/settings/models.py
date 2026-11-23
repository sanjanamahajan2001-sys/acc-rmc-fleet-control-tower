"""
PostgreSQL Platform Configuration Registry Models
Workstream X.3 Production Models
"""

import datetime
import uuid
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class ConfigurationCategory(Base):
    __tablename__ = "configuration_categories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    icon = Column(String(64), default="Settings", nullable=False)
    display_order = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)


class PlatformConfiguration(Base):
    __tablename__ = "platform_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain = Column(String(64), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    sub_category = Column(String(64), nullable=True)
    key = Column(String(128), nullable=False, index=True)
    value = Column(JSONB, nullable=False)
    value_type = Column(String(32), default="STRING", nullable=False)
    unit = Column(String(32), nullable=True)
    default_value = Column(JSONB, nullable=True)
    editable = Column(Boolean, default=True, nullable=False)
    is_secret = Column(Boolean, default=False, nullable=False)
    requires_restart = Column(Boolean, default=False, nullable=False)
    validation_type = Column(String(32), default="NONE", nullable=False)
    validation_rules = Column(JSONB, nullable=True)
    display_order = Column(Integer, default=0, nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(128), default="SYSTEM", nullable=False)
    updated_by = Column(String(128), default="SYSTEM", nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    history = relationship("PlatformConfigurationHistory", back_populates="configuration", cascade="all, delete-orphan")


class PlatformConfigurationHistory(Base):
    __tablename__ = "platform_configuration_histories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    configuration_id = Column(UUID(as_uuid=True), ForeignKey("platform_configurations.id", ondelete="CASCADE"), nullable=False)
    previous_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=False)
    changed_by = Column(String(128), default="SYSTEM", nullable=False)
    change_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc), index=True)

    configuration = relationship("PlatformConfiguration", back_populates="history")
