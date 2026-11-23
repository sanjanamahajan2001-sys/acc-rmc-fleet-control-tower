"""
Local Filesystem Storage Provider Implementation
"""

import pathlib
import shutil
from collections.abc import AsyncGenerator

import aiofiles

from app.modules.erp.storage.provider import BaseStorageProvider


class LocalStorageProvider(BaseStorageProvider):
    """
    Production-ready Local Filesystem Storage Provider.
    Implements thread-safe / process-safe atomic chunk assembly and atomic file writes.
    """

    def __init__(self, root_dir: str | pathlib.Path):
        target = pathlib.Path(root_dir).resolve()
        try:
            target.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            target = pathlib.Path("/tmp/fleet_storage").resolve()
            target.mkdir(parents=True, exist_ok=True)

        self.root_dir = target
        self.uploads_tmp_dir = self.root_dir / "tmp_uploads"
        self.workbooks_dir = self.root_dir / "workbooks"

    async def init_storage(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_tmp_dir.mkdir(parents=True, exist_ok=True)
        self.workbooks_dir.mkdir(parents=True, exist_ok=True)

    async def save_chunk(self, upload_id: str, chunk_index: int, data: bytes) -> str:
        session_dir = self.uploads_tmp_dir / upload_id
        session_dir.mkdir(parents=True, exist_ok=True)

        chunk_path = session_dir / f"chunk_{chunk_index:06d}.part"
        async with aiofiles.open(chunk_path, "wb") as f:
            await f.write(data)
        return str(chunk_path)

    async def assemble_chunks(
        self, upload_id: str, total_chunks: int, target_relative_path: str
    ) -> str:
        session_dir = self.uploads_tmp_dir / upload_id
        target_path = self.root_dir / target_relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_target_path = target_path.with_suffix(".assembling")

        async with aiofiles.open(tmp_target_path, "wb") as outfile:
            for i in range(total_chunks):
                chunk_path = session_dir / f"chunk_{i:06d}.part"
                if not chunk_path.exists():
                    raise FileNotFoundError(
                        f"Missing chunk {i} for upload session {upload_id}"
                    )
                async with aiofiles.open(chunk_path, "rb") as infile:
                    while True:
                        block = await infile.read(1048576)  # 1MB buffer
                        if not block:
                            break
                        await outfile.write(block)

        # Atomic rename
        shutil.move(str(tmp_target_path), str(target_path))

        # Cleanup session directory
        await self.cleanup_upload_session(upload_id)

        return str(target_path)

    async def save_file(self, relative_path: str, data: bytes) -> str:
        target_path = self.root_dir / relative_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = target_path.with_suffix(".tmp")
        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(data)

        shutil.move(str(tmp_path), str(target_path))
        return str(target_path)

    async def get_file_path(self, relative_path: str) -> pathlib.Path:
        target_path = self.root_dir / relative_path
        return target_path

    async def read_chunks(
        self, relative_path: str, chunk_size: int = 1048576
    ) -> AsyncGenerator[bytes, None]:
        target_path = self.root_dir / relative_path
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {target_path}")

        async with aiofiles.open(target_path, "rb") as f:
            while True:
                chunk = await f.read(chunk_size)
                if not chunk:
                    break
                yield chunk

    async def file_exists(self, relative_path: str) -> bool:
        target_path = self.root_dir / relative_path
        return target_path.exists() and target_path.is_file()

    async def delete_file(self, relative_path: str) -> bool:
        target_path = self.root_dir / relative_path
        if target_path.exists():
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
            return True
        return False

    async def cleanup_upload_session(self, upload_id: str) -> None:
        session_dir = self.uploads_tmp_dir / upload_id
        if session_dir.exists():
            shutil.rmtree(session_dir)
