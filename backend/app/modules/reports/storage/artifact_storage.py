import os
from typing import Dict, Any


REPORTS_BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../storage/reports")
)

from pathlib import Path

class ReportArtifactStorage:
    @staticmethod
    def _get_base_path() -> Path:
        return Path(REPORTS_BASE_DIR).resolve()

    @classmethod
    def _get_execution_dir(cls, execution_id: str) -> str:
        if not execution_id or ".." in execution_id or "/" in execution_id or "\\" in execution_id:
            raise ValueError(f"Invalid execution directory traversal attempt: {execution_id}")
        
        base_path = cls._get_base_path()
        clean_id = os.path.basename(execution_id)
        target_path = (base_path / clean_id).resolve()

        if not str(target_path).startswith(str(base_path)) or target_path == base_path:
            raise ValueError(f"Invalid execution directory traversal attempt: {execution_id}")

        os.makedirs(target_path, exist_ok=True)
        return str(target_path)

    @classmethod
    def save_artifacts(cls, execution_id: str, artifacts: Dict[str, bytes]) -> Dict[str, str]:
        """
        Saves rendered report bytes (json, pdf, xlsx) into storage/reports/{execution_id}/.
        Returns a dict of saved file paths keyed by format.
        """
        target_dir = cls._get_execution_dir(execution_id)
        saved_paths = {}
        
        for fmt, content in artifacts.items():
            filename = f"dispatch_analysis_report.{fmt.lower()}"
            filepath = os.path.join(target_dir, filename)
            with open(filepath, "wb") as f:
                f.write(content)
            saved_paths[fmt.lower()] = filepath
            
        return saved_paths

    @classmethod
    def get_artifact_path(cls, execution_id: str, format_ext: str) -> str:
        if not execution_id or ".." in execution_id or "/" in execution_id or "\\" in execution_id:
            raise FileNotFoundError(f"Invalid execution directory traversal attempt: {execution_id}")
        
        base_path = cls._get_base_path()
        clean_id = os.path.basename(execution_id)
        fmt = format_ext.lower().strip(".")
        filename = f"dispatch_analysis_report.{fmt}"
        target_path = (base_path / clean_id / filename).resolve()
        
        if not str(target_path).startswith(str(base_path)) or not target_path.exists():
            raise FileNotFoundError(f"Report artifact not found for execution {execution_id} format {format_ext}")
            
        return str(target_path)

    @classmethod
    def purge_execution_artifacts(cls, execution_id: str) -> int:
        """
        Deletes all stored artifact files for a specific execution directory safely.
        Returns total bytes reclaimed.
        """
        if not execution_id or ".." in execution_id or "/" in execution_id or "\\" in execution_id:
            raise ValueError(f"Invalid execution directory traversal attempt: {execution_id}")
        
        base_path = cls._get_base_path()
        clean_id = os.path.basename(execution_id)
        target_path = (base_path / clean_id).resolve()

        if not str(target_path).startswith(str(base_path)) or target_path == base_path:
            raise ValueError(f"Invalid execution directory traversal attempt: {execution_id}")

        reclaimed_bytes = 0
        if target_path.exists() and target_path.is_dir():
            for child in target_path.iterdir():
                if child.is_file():
                    reclaimed_bytes += child.stat().st_size
                    child.unlink()
            try:
                target_path.rmdir()
            except Exception:
                pass
        return reclaimed_bytes

    @classmethod
    def cleanup_orphan_directories(cls, valid_execution_ids: set) -> int:
        """
        Deletes storage directories that have no matching active execution record.
        Returns count of orphan directories purged.
        """
        base_path = cls._get_base_path()
        if not base_path.exists():
            return 0

        purged_orphans = 0
        for item in base_path.iterdir():
            if item.is_dir() and item.name not in valid_execution_ids:
                for child in item.iterdir():
                    if child.is_file():
                        child.unlink()
                try:
                    item.rmdir()
                    purged_orphans += 1
                except Exception:
                    pass
        return purged_orphans


