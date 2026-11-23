"""
PostgreSQL Schema Metadata Introspection Service
Workstream: Settings Center Database Preview

Queries live PostgreSQL system catalogs / information_schema to extract:
- Tables (public schema, BASE TABLE)
- Columns (names, types, nullability, ordinal position)
- Primary Key constraints
- Foreign Key constraints and referenced targets
- Clean DDL SQL export generation
"""

import structlog
from typing import List, Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.schemas_db_preview import (
    DatabaseColumnDTO,
    DatabaseTableDTO,
    DatabaseSchemaResponseDTO,
    DatabaseSqlExportResponseDTO,
)

logger = structlog.get_logger(__name__)


class DatabaseSchemaIntrospectionService:
    """
    Production-safe PostgreSQL metadata introspection service.
    Zero mock data; queries live information_schema.
    """

    @classmethod
    async def get_database_schema(
        cls,
        session: AsyncSession,
        database_name: str = "fleet_control_tower_db",
    ) -> DatabaseSchemaResponseDTO:
        """
        Extracts the full public schema structure directly from PostgreSQL.
        """
        # 1. Fetch all public base tables
        tables_query = text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        res_tables = await session.execute(tables_query)
        table_names = [r[0] for r in res_tables.fetchall()]

        # 2. Fetch all columns with metadata
        columns_query = text("""
            SELECT 
                c.table_name,
                c.column_name,
                c.data_type,
                c.udt_name,
                c.is_nullable,
                c.column_default,
                c.ordinal_position
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
            ORDER BY c.table_name, c.ordinal_position;
        """)
        res_cols = await session.execute(columns_query)
        cols_by_table: Dict[str, List[Dict[str, Any]]] = {}
        for r in res_cols.fetchall():
            t_name = r[0]
            if t_name not in cols_by_table:
                cols_by_table[t_name] = []
            cols_by_table[t_name].append({
                "column_name": r[1],
                "data_type": r[2],
                "udt_name": r[3],
                "is_nullable": r[4] == "YES",
                "column_default": r[5],
                "ordinal_position": r[6],
            })

        # 3. Fetch Primary Key constraints
        pk_query = text("""
            SELECT
                tc.table_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.ordinal_position;
        """)
        res_pks = await session.execute(pk_query)
        pks_by_table: Dict[str, List[str]] = {}
        for r in res_pks.fetchall():
            t_name, col_name = r[0], r[1]
            if t_name not in pks_by_table:
                pks_by_table[t_name] = []
            pks_by_table[t_name].append(col_name)

        # 4. Fetch Foreign Key constraints
        fk_query = text("""
            SELECT
                tc.table_name AS source_table,
                kcu.column_name AS source_column,
                ccu.table_name AS target_table,
                ccu.column_name AS target_column,
                tc.constraint_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name;
        """)
        res_fks = await session.execute(fk_query)
        fks_by_table_col: Dict[Tuple[str, str], Tuple[str, str]] = {}
        fks_by_table: Dict[str, List[Dict[str, str]]] = {}
        total_fk_count = 0

        for r in res_fks.fetchall():
            s_table, s_col, t_table, t_col = r[0], r[1], r[2], r[3]
            fks_by_table_col[(s_table, s_col)] = (t_table, t_col)
            if s_table not in fks_by_table:
                fks_by_table[s_table] = []
            fks_by_table[s_table].append({
                "column": s_col,
                "target_table": t_table,
                "target_column": t_col,
            })
            total_fk_count += 1

        # 5. Assemble structured DTOs
        table_dtos: List[DatabaseTableDTO] = []
        for t_name in table_names:
            raw_columns = cols_by_table.get(t_name, [])
            pk_list = pks_by_table.get(t_name, [])
            fk_list = fks_by_table.get(t_name, [])

            col_dtos: List[DatabaseColumnDTO] = []
            for col in raw_columns:
                c_name = col["column_name"]
                is_pk = c_name in pk_list
                fk_target = fks_by_table_col.get((t_name, c_name))

                # Normalize data type display (e.g. udt_name or clean type)
                dtype_display = col["data_type"].title() if col["data_type"] else col["udt_name"].title()
                if col["data_type"] == "character varying":
                    dtype_display = "Character Varying"
                elif col["data_type"] == "timestamp with time zone":
                    dtype_display = "Timestamp With Time Zone"
                elif col["data_type"] == "timestamp without time zone":
                    dtype_display = "Timestamp Without Time Zone"
                elif col["data_type"] == "USER-DEFINED":
                    dtype_display = col["udt_name"].upper()

                col_dtos.append(
                    DatabaseColumnDTO(
                        name=c_name,
                        data_type=dtype_display,
                        udt_name=col["udt_name"],
                        is_nullable=col["is_nullable"],
                        is_primary_key=is_pk,
                        is_foreign_key=fk_target is not None,
                        foreign_key_target_table=fk_target[0] if fk_target else None,
                        foreign_key_target_column=fk_target[1] if fk_target else None,
                        column_default=col["column_default"],
                        ordinal_position=col["ordinal_position"],
                    )
                )

            table_dtos.append(
                DatabaseTableDTO(
                    table_name=t_name,
                    column_count=len(col_dtos),
                    primary_keys=pk_list,
                    foreign_keys=fk_list,
                    columns=col_dtos,
                )
            )

        logger.info(
            "Database schema introspected successfully",
            table_count=len(table_dtos),
            foreign_key_count=total_fk_count,
        )

        total_column_count = sum(t.column_count for t in table_dtos)
        return DatabaseSchemaResponseDTO(
            database_name=database_name,
            table_count=len(table_dtos),
            column_count=total_column_count,
            foreign_key_count=total_fk_count,
            tables=table_dtos,
        )

    @classmethod
    async def generate_sql_export(
        cls,
        session: AsyncSession,
        database_name: str = "fleet_control_tower_db",
    ) -> DatabaseSqlExportResponseDTO:
        """
        Generates clean, read-only SQL DDL export for all tables and foreign keys.
        """
        schema_data = await cls.get_database_schema(session, database_name)

        sql_lines = [
            f"-- ============================================================================",
            f"-- Fleet Control Tower Database Schema Export",
            f"-- Database: {database_name}",
            f"-- Tables: {schema_data.table_count} | Foreign Keys: {schema_data.foreign_key_count}",
            f"-- Generated At (UTC): {schema_data.generated_at}",
            f"-- ============================================================================\n",
        ]

        # 1. Table Definitions
        for t in schema_data.tables:
            sql_lines.append(f"CREATE TABLE IF NOT EXISTS public.{t.table_name} (")
            col_defs = []
            for col in t.columns:
                null_str = "" if col.is_nullable else " NOT NULL"
                default_str = f" DEFAULT {col.column_default}" if col.column_default else ""
                col_defs.append(f"    {col.name} {col.data_type.upper()}{null_str}{default_str}")

            if t.primary_keys:
                pk_cols = ", ".join(t.primary_keys)
                col_defs.append(f"    CONSTRAINT pk_{t.table_name} PRIMARY KEY ({pk_cols})")

            sql_lines.append(",\n".join(col_defs))
            sql_lines.append(");\n")

        # 2. Foreign Key Constraints
        sql_lines.append("-- Foreign Key Constraints")
        for t in schema_data.tables:
            for fk in t.foreign_keys:
                sql_lines.append(
                    f"ALTER TABLE public.{t.table_name} ADD CONSTRAINT fk_{t.table_name}_{fk['column']} "
                    f"FOREIGN KEY ({fk['column']}) REFERENCES public.{fk['target_table']} ({fk['target_column']});"
                )

        return DatabaseSqlExportResponseDTO(
            sql_script="\n".join(sql_lines),
            table_count=schema_data.table_count,
        )
