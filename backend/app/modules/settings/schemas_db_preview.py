"""
Pydantic DTOs for Database Schema Preview & Introspection
Workstream: Settings Center Database Preview
"""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class DatabaseColumnDTO(BaseModel):
    name: str
    data_type: str
    udt_name: str
    is_nullable: bool
    is_primary_key: bool = False
    is_foreign_key: bool = False
    foreign_key_target_table: Optional[str] = None
    foreign_key_target_column: Optional[str] = None
    column_default: Optional[str] = None
    ordinal_position: int


class DatabaseTableDTO(BaseModel):
    table_name: str
    column_count: int
    primary_keys: List[str] = Field(default_factory=list)
    foreign_keys: List[Dict[str, str]] = Field(default_factory=list)
    columns: List[DatabaseColumnDTO] = Field(default_factory=list)


class DatabaseSchemaResponseDTO(BaseModel):
    database_name: str
    table_count: int
    column_count: int
    foreign_key_count: int
    tables: List[DatabaseTableDTO]
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DatabaseSqlExportResponseDTO(BaseModel):
    sql_script: str
    table_count: int
    exported_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
