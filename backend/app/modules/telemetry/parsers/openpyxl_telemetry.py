"""
Streaming OpenPyXL Workbook Parser for Telemetry Workbooks
Parses Trip Drum July & August.xlsx stream into ParsedTelemetryRowDTO batches.
"""

import datetime
import pathlib
from typing import Any, AsyncGenerator

import openpyxl
from app.modules.telemetry.schemas import ParsedTelemetryRowDTO


class OpenPyXLTelemetryParser:
    """
    Production-Grade Streaming Parser for Fleet Telemetry Excel Workbooks.
    """

    def _parse_datetime(self, val: Any) -> datetime.datetime | None:
        if isinstance(val, datetime.datetime):
            return val
        if isinstance(val, datetime.time):
            today = datetime.date.today()
            return datetime.datetime.combine(today, val)
        if isinstance(val, str) and val.strip():
            try:
                return datetime.datetime.fromisoformat(val.strip())
            except ValueError:
                pass
        return None

    def _parse_float(self, val: Any) -> float | None:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _parse_combined_datetime(self, date_val: Any, time_val: Any) -> datetime.datetime | None:
        d_obj = None
        if isinstance(date_val, datetime.datetime):
            d_obj = date_val.date()
        elif isinstance(date_val, datetime.date):
            d_obj = date_val
        elif isinstance(date_val, str) and date_val.strip() and "no drum" not in date_val.lower():
            try:
                d_obj = datetime.date.fromisoformat(date_val.strip().split()[0])
            except ValueError:
                pass

        if not d_obj:
            return None

        t_obj = datetime.time(0, 0, 0)
        if isinstance(time_val, datetime.time):
            t_obj = time_val
        elif isinstance(time_val, str) and time_val.strip():
            try:
                parts = [int(p) for p in time_val.strip().split(":")]
                if len(parts) >= 2:
                    t_obj = datetime.time(parts[0], parts[1], parts[2] if len(parts) > 2 else 0)
            except ValueError:
                pass

        return datetime.datetime.combine(d_obj, t_obj, tzinfo=datetime.timezone.utc)

    async def parse_workbook_batches(
        self, file_path: pathlib.Path, batch_size: int = 1000
    ) -> AsyncGenerator[list[ParsedTelemetryRowDTO], None]:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb.active or wb.worksheets[0]

        headers: list[str] = []
        current_batch: list[ParsedTelemetryRowDTO] = []
        row_idx = 0

        for row in sheet.iter_rows(values_only=True):
            row_idx += 1
            if not row or not any(row):
                continue

            # Look for Row 6 true header containing 'trip no'
            if not headers:
                row_str = [str(c).strip().lower() if c is not None else "" for c in row]
                if "trip no" in row_str or "ticket number" in row_str or "vehicle" in row_str:
                    headers = [c if c else f"col_{i}" for i, c in enumerate(row_str)]
                continue

            # Skip unit subtitle row (e.g. Row 7 with '(Km/h)')
            row_0_str = str(row[0]).strip().lower() if row[0] is not None else ""
            if row_0_str in ["kms", "(km/h)", "(hh:mm)", "dharagal", ""] and not row[1] and not row[2]:
                continue

            row_dict = {headers[i]: row[i] for i in range(min(len(headers), len(row)))}

            # Extract exact 30 columns
            trip_no = str(row_dict.get("trip no") or f"TRIP-{row_idx}")
            ticket_no = str(row_dict.get("ticket number") or "")
            v_code = str(row_dict.get("vehicle") or "DEFAULT_VEHICLE")
            p_name = str(row_dict.get("plant name") or "DEFAULT_PLANT")
            batching_name = str(row_dict.get("batching name") or p_name)

            p_out_ts = self._parse_combined_datetime(row_dict.get("plant out date"), row_dict.get("plant out time"))
            s_in_ts = self._parse_combined_datetime(row_dict.get("site in date"), row_dict.get("site in time"))
            s_out_ts = self._parse_combined_datetime(row_dict.get("site out date"), row_dict.get("site out time"))
            p_in_ts = self._parse_combined_datetime(row_dict.get("plant in date"), row_dict.get("plant in time"))

            max_spd = self._parse_float(row_dict.get("max speed"))
            avg_spd = self._parse_float(row_dict.get("average speed"))

            # Drum Rotation Hours (Col 30): Convert time object or float to decimal hours
            rot_val = row_dict.get("drum rotation hours")
            drum_rot_hrs = None
            if isinstance(rot_val, datetime.time):
                drum_rot_hrs = round(rot_val.hour + rot_val.minute / 60.0 + rot_val.second / 3600.0, 2)
            elif isinstance(rot_val, (int, float)):
                drum_rot_hrs = float(rot_val)

            # Drum Stop Duration (Col 29): Calculate stop duration in minutes or parse timestamp
            stop_val = row_dict.get("drum stop time")
            stop_duration_mins = None
            if isinstance(stop_val, datetime.datetime) and p_out_ts:
                if stop_val.tzinfo is None:
                    stop_val = stop_val.replace(tzinfo=datetime.timezone.utc)
                stop_duration_mins = round(abs((stop_val - p_out_ts).total_seconds()) / 60.0, 1)
            elif isinstance(stop_val, (int, float)):
                stop_duration_mins = float(stop_val)

            dto = ParsedTelemetryRowDTO(
                row_number=row_idx,
                sheet_name=sheet.title,
                trip_number=trip_no,
                vehicle_code=v_code,
                plant_code=p_name,
                site_name=str(row_dict.get("unloading place") or "DEFAULT_SITE"),
                plant_out_timestamp=p_out_ts,
                site_arrival_timestamp=s_in_ts,
                unloading_start_timestamp=s_in_ts,
                unloading_end_timestamp=s_out_ts,
                site_departure_timestamp=s_out_ts,
                plant_return_timestamp=p_in_ts,
                max_speed_kmh=max_spd,
                avg_speed_kmh=avg_spd,
                drum_rotation_rpm=drum_rot_hrs,
                drum_stop_duration_mins=stop_duration_mins,
                raw_data=row_dict,
            )
            current_batch.append(dto)

            if len(current_batch) >= batch_size:
                yield current_batch
                current_batch = []

        if current_batch:
            yield current_batch

        wb.close()
