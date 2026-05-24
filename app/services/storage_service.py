import json
import logging
import os
from datetime import datetime

from anyio import to_thread

from app.schemas.company import CompanyInStorage
from app.services.config import settings

logger = logging.getLogger(__name__)

class CompanyStorage:
    def __init__(self, file_path: str = settings.STORAGE_FILE_PATH):
        self.file_path = file_path
        logger.info(f"CompanyStorage initialized with file_path={file_path}")

    async def _read_all(self) -> list[dict]:
        logger.debug(f"_read_all() calling _read_sync via thread")
        return await to_thread.run_sync(self._read_sync)

    def _read_sync(self) -> list[dict]:
        logger.debug(f"_read_sync() reading from {self.file_path}")
        if not os.path.exists(self.file_path):
            logger.warning(f"File does not exist: {self.file_path}, returning empty list")
            return []
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
                logger.info(f"Successfully read {len(data)} companies from {self.file_path}")
                return data
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"JSON decode error reading {self.file_path}: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Error reading {self.file_path}: {e}", exc_info=True)
            return []

    async def _write_all(self, companies: list[dict]):
        logger.debug(f"_write_all() writing {len(companies)} companies via thread")
        await to_thread.run_sync(self._write_sync, companies)

    def _write_sync(self, companies: list[dict]):
        logger.info(f"_write_sync() writing {len(companies)} companies to {self.file_path}")
        def datetime_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")

        temp_file = f"{self.file_path}.tmp"
        try:
            with open(temp_file, "w") as f:
                json.dump(companies, f, indent=2, default=datetime_serializer)
                f.flush()
                os.fsync(f.fileno())
            logger.debug(f"Temp file written, replacing {self.file_path} with {temp_file}")
            os.replace(temp_file, self.file_path)
            logger.info(f"Successfully wrote {len(companies)} companies to {self.file_path}")
        except Exception as e:
            logger.error(f"Error writing to storage: {e}", exc_info=True)
            if os.path.exists(temp_file):
                logger.debug(f"Cleaning up temp file {temp_file}")
                os.remove(temp_file)
            raise

    async def list_companies(self) -> list[CompanyInStorage]:
        logger.info("list_companies() called")
        try:
            data = await self._read_all()
            companies = [CompanyInStorage(**c) for c in data]
            logger.info(f"list_companies() completed, returning {len(companies)} companies")
            return companies
        except Exception as e:
            logger.error(f"Error in list_companies(): {e}", exc_info=True)
            raise

    async def get_company(self, company_id: str) -> CompanyInStorage | None:
        logger.info(f"get_company(company_id={company_id}) called")
        try:
            companies = await self._read_all()
            for c in companies:
                if c["id"] == company_id:
                    logger.info(f"Found company_id={company_id}")
                    return CompanyInStorage(**c)
            logger.warning(f"Company not found: company_id={company_id}")
            return None
        except Exception as e:
            logger.error(f"Error in get_company(company_id={company_id}): {e}", exc_info=True)
            raise

    async def create_company(self, company: CompanyInStorage) -> CompanyInStorage:
        logger.info(f"create_company(company_id={company.id}, name={company.name}) called")
        try:
            companies = await self._read_all()
            logger.debug(f"Currently {len(companies)} companies in storage")
            companies.append(company.model_dump())
            await self._write_all(companies)
            logger.info(f"Successfully created company_id={company.id}, now {len(companies)} total companies")
            return company
        except Exception as e:
            logger.error(f"Error in create_company(company_id={company.id}): {e}", exc_info=True)
            raise

    async def update_company(self, company_id: str, company_data: dict) -> CompanyInStorage | None:
        logger.info(f"update_company(company_id={company_id}) called with data keys={list(company_data.keys())}")
        try:
            companies = await self._read_all()
            for i, c in enumerate(companies):
                if c["id"] == company_id:
                    logger.debug(f"Found company at index {i}, applying updates: {list(company_data.keys())}")
                    companies[i].update(company_data)
                    updated = CompanyInStorage(**companies[i])
                    await self._write_all(companies)
                    logger.info(f"Successfully updated company_id={company_id}")
                    return updated
            logger.warning(f"Company not found for update: company_id={company_id}")
            return None
        except Exception as e:
            logger.error(f"Error in update_company(company_id={company_id}): {e}", exc_info=True)
            raise

    async def delete_company(self, company_id: str) -> bool:
        """Soft-delete: sets is_active=False instead of removing the record."""
        logger.info(f"delete_company(company_id={company_id}) called — soft delete")
        try:
            companies = await self._read_all()
            for i, c in enumerate(companies):
                if c["id"] == company_id:
                    logger.debug(f"Found company at index {i}, setting is_active=False")
                    companies[i]["is_active"] = False
                    from datetime import datetime, timezone
                    companies[i]["updated_at"] = datetime.now(timezone.utc).isoformat()
                    await self._write_all(companies)
                    logger.info(f"Successfully soft-deleted company_id={company_id}")
                    return True
            logger.warning(f"Company not found for soft-delete: company_id={company_id}")
            return False
        except Exception as e:
            logger.error(f"Error in delete_company(company_id={company_id}): {e}", exc_info=True)
            raise
