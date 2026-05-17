import json
import os
import fcntl
from datetime import datetime
from anyio import to_thread
from app.schemas.company import CompanyInStorage
from app.services.config import settings

class CompanyStorage:
    def __init__(self, file_path: str = settings.STORAGE_FILE_PATH):
        self.file_path = file_path

    async def _read_all(self) -> list[dict]:
        return await to_thread.run_sync(self._read_sync)

    def _read_sync(self) -> list[dict]:
        if not os.path.exists(self.file_path):
            return []
        with open(self.file_path, "r") as f:
            try:
                # Shared lock for reading
                fcntl.flock(f, fcntl.LOCK_SH)
                data = json.load(f)
                fcntl.flock(f, fcntl.LOCK_UN)
                return data
            except (json.JSONDecodeError, ValueError):
                return []

    async def _write_all(self, companies: list[dict]):
        await to_thread.run_sync(self._write_sync, companies)

    def _write_sync(self, companies: list[dict]):
        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        temp_file = f"{self.file_path}.tmp"
        # Open the main file to acquire an exclusive lock
        # This ensures that even if we are writing to a temp file, 
        # other processes trying to write will wait on this lock.
        lock_file_path = f"{self.file_path}.lock"
        
        with open(lock_file_path, "w") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                with open(temp_file, "w") as f:
                    json.dump(companies, f, indent=2, default=datetime_serializer)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_file, self.file_path)
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)

    async def list_companies(self) -> list[CompanyInStorage]:
        data = await self._read_all()
        return [CompanyInStorage(**c) for c in data]

    async def get_company(self, company_id: str) -> CompanyInStorage | None:
        companies = await self._read_all()
        for c in companies:
            if c["id"] == company_id:
                return CompanyInStorage(**c)
        return None

    async def create_company(self, company: CompanyInStorage) -> CompanyInStorage:
        companies = await self._read_all()
        companies.append(company.model_dump())
        await self._write_all(companies)
        return company

    async def update_company(self, company_id: str, company_data: dict) -> CompanyInStorage | None:
        companies = await self._read_all()
        for i, c in enumerate(companies):
            if c["id"] == company_id:
                companies[i].update(company_data)
                updated = CompanyInStorage(**companies[i])
                await self._write_all(companies)
                return updated
        return None

    async def delete_company(self, company_id: str) -> bool:
        companies = await self._read_all()
        initial_len = len(companies)
        companies = [c for c in companies if c["id"] != company_id]
        if len(companies) < initial_len:
            await self._write_all(companies)
            return True
        return False
