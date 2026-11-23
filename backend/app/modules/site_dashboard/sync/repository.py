"""
Workstream 2.11 Synchronization Repository Layer
Executes database queries for ERP import logs, record counts, and canonical snapshot checksums.
"""

import hashlib
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import Dispatch


class SyncRepository:
    """Queries canonical database state for real-time synchronization tracking."""

    @staticmethod
    async def get_latest_db_state(session: AsyncSession) -> dict[str, Any]:
        """Queries record counts and max dispatch dates to compute canonical E-Tag snapshot checksum."""
        count_stmt = select(func.count(Dispatch.id))
        max_date_stmt = select(func.max(Dispatch.dispatch_date))

        total_records = (await session.execute(count_stmt)).scalar() or 0
        max_date = (await session.execute(max_date_stmt)).scalar()

        date_str = str(max_date or "2025-08-15")
        clean_date = date_str.split("+")[0].replace("T", " ")[:10]

        # Compute deterministic E-Tag MD5 hash checksum
        raw_checksum_src = f"records={total_records}:date={clean_date}"
        e_tag = hashlib.md5(raw_checksum_src.encode("utf-8")).hexdigest()
        snapshot_ver = f"v2.11-SNAP-{clean_date.replace('-', '')}" if total_records > 0 else "v2.11-SNAP-EMPTY"

        return {
            "total_records": int(total_records),
            "latest_date": clean_date,
            "max_id": 0,
            "e_tag": e_tag,
            "snapshot_version": snapshot_ver,
        }
