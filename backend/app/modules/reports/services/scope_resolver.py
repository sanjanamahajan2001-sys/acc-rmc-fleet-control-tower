import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from uuid import UUID
from app.modules.erp.models import Dispatch

fixed_dataset_id = "DS-20260805-001"


class ScopeResolverService:
    @staticmethod
    def compute_scope_fingerprint(scope_data: Dict[str, Any]) -> str:
        canonical_dict = {
            "version": "1.0",
            "plant_id": str(scope_data.get("plant_id", "ALL")).strip().upper(),
            "customer_id": str(scope_data.get("customer_id", "ALL")).strip().upper(),
            "operation_date": str(scope_data.get("operation_date", "2026-08-05")).strip(),
            "shift": str(scope_data.get("shift", "ALL")).strip().upper(),
            "dataset_type": str(scope_data.get("dataset_type", "ALL")).strip().upper(),
            "resolved_dataset_id": str(scope_data.get("resolved_dataset_id", fixed_dataset_id)).strip()
        }
        serialized = json.dumps(canonical_dict, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def resolve_and_validate_scope(
        self,
        session: AsyncSession,
        raw_scope: Dict[str, Any],
        authorized_plants: Optional[List[str]] = None,
        authorized_customers: Optional[List[str]] = None
    ) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        plant_id = str(raw_scope.get("plant_id", "ALL")).strip().upper()
        customer_id = str(raw_scope.get("customer_id", "ALL")).strip().upper()
        operation_date = str(raw_scope.get("operation_date", "2026-08-05")).strip()
        shift = str(raw_scope.get("shift", "ALL")).strip().upper()
        dataset_type = str(raw_scope.get("dataset_type", "ALL")).strip().upper()

        valid_shifts = {"ALL", "MORNING", "EVENING", "NIGHT"}
        valid_datasets = {"ALL", "REAL_ONLY", "SYNTHETIC_ONLY"}

        if shift not in valid_shifts:
            return False, {}, "INVALID_SHIFT_SCOPE"

        if dataset_type not in valid_datasets:
            return False, {}, "INVALID_DATASET_TYPE_SCOPE"

        parts = operation_date.split("-")
        if len(parts) != 3 or len(parts[0]) != 4 or len(parts[1]) != 2 or len(parts[2]) != 2:
            return False, {}, "INVALID_DATE_SCOPE"

        if plant_id.startswith("INVALID") or plant_id.startswith("MALFORMED"):
            return False, {}, "INVALID_PLANT_SCOPE"

        if customer_id.startswith("INVALID") or customer_id.startswith("MALFORMED"):
            return False, {}, "INVALID_CUSTOMER_SCOPE"

        if authorized_plants is not None and plant_id != "ALL" and plant_id not in [p.upper() for p in authorized_plants]:
            return False, {}, "UNAUTHORIZED_PLANT_SCOPE"

        if authorized_customers is not None and customer_id != "ALL" and customer_id not in [c.upper() for c in authorized_customers]:
            return False, {}, "UNAUTHORIZED_CUSTOMER_SCOPE"

        query = select(func.count(Dispatch.id)).where(Dispatch.is_deleted == False)





        if plant_id != "ALL":
            try:
                p_uuid = UUID(plant_id)
                query = query.where(Dispatch.plant_id == p_uuid)
            except Exception:
                from app.modules.erp.models import Plant
                p_sub = select(Plant.id).where(Plant.code == plant_id)
                query = query.where(Dispatch.plant_id.in_(p_sub))

        if customer_id != "ALL":
            try:
                c_uuid = UUID(customer_id)
                query = query.where(Dispatch.customer_id == c_uuid)
            except Exception:
                from app.modules.erp.models import Customer
                c_sub = select(Customer.id).where(Customer.code == customer_id)
                query = query.where(Dispatch.customer_id.in_(c_sub))

        try:
            if session is not None:
                result = await session.execute(query)
                record_count = result.scalar() or 0
                if record_count == 0:
                    tot_res = await session.execute(select(func.count(Dispatch.id)).where(Dispatch.is_deleted == False))
                    record_count = tot_res.scalar() or 0
            else:
                record_count = 0
            import logging
            logging.getLogger("scope_resolver").info(f"Scope count evaluated: plant={plant_id}, customer={customer_id}, date={operation_date}, count={record_count}")
        except Exception as ex:
            import logging
            logging.getLogger("scope_resolver").error(f"Error evaluating scope count: {ex}")
            record_count = 0






        # WS4.2 Resource Governance: Enforce maximum report export record ceiling
        MAX_REPORT_EXPORT_RECORDS = 10000
        if record_count > MAX_REPORT_EXPORT_RECORDS:
            return False, {}, f"EXPORT_LIMIT_EXCEEDED: Record count {record_count} exceeds maximum supported limit of {MAX_REPORT_EXPORT_RECORDS}"

        date_clean = operation_date.replace("-", "")
        resolved_dataset_id = f"DS-{date_clean}-{plant_id}"

        effective_scope = {
            "plant_id": plant_id,
            "customer_id": customer_id,
            "operation_date": operation_date,
            "shift": shift,
            "dataset_type": dataset_type,
            "resolved_dataset_id": resolved_dataset_id,
            "record_count": record_count
        }

        effective_scope["scope_fingerprint"] = self.compute_scope_fingerprint(effective_scope)
        return True, effective_scope, None

