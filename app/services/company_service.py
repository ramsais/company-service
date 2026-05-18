import uuid
import logging
from datetime import datetime, timezone
from app.schemas.company import Company, CompanyCreate, CompanyUpdate, CompanyInStorage
from app.services.storage_service import CompanyStorage

logger = logging.getLogger(__name__)


class CompanyService:
    def __init__(self, storage: CompanyStorage):
        self.storage = storage
        logger.info(f"CompanyService initialized with storage_file_path={storage.file_path}")

    async def list_companies(self) -> list[Company]:
        logger.info("list_companies() called")
        try:
            companies_storage = await self.storage.list_companies()
            logger.info(f"Retrieved {len(companies_storage)} companies from storage")
            result = [Company(**c.model_dump()) for c in companies_storage]
            logger.info(f"list_companies() completed, returning {len(result)} companies")
            return result
        except Exception as e:
            logger.error(f"Error in list_companies(): {e}", exc_info=True)
            raise

    async def get_company(self, company_id: str) -> Company | None:
        logger.info(f"get_company(company_id={company_id}) called")
        try:
            c_storage = await self.storage.get_company(company_id)
            if not c_storage:
                logger.warning(f"Company not found for company_id={company_id}")
                return None
            company = Company(**c_storage.model_dump())
            logger.info(f"get_company(company_id={company_id}) completed")
            return company
        except Exception as e:
            logger.error(f"Error in get_company(company_id={company_id}): {e}", exc_info=True)
            raise

    async def create_company(self, company_in: CompanyCreate) -> Company:
        logger.info(f"create_company() called with name={company_in.name}")
        try:
            company_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            logger.debug(f"Generated company_id={company_id}, now={now.isoformat()}")

            c_storage = CompanyInStorage(
                id=company_id,
                created_at=now,
                updated_at=now,
                **company_in.model_dump()
            )
            await self.storage.create_company(c_storage)
            logger.info(f"Successfully persisted company_id={company_id} to storage")

            company = Company(**c_storage.model_dump())
            logger.info(f"create_company() completed for company_id={company_id}")
            return company
        except Exception as e:
            logger.error(f"Error in create_company(): {e}", exc_info=True)
            raise

    async def update_company(self, company_id: str, company_in: CompanyUpdate) -> Company | None:
        update_fields = company_in.model_dump(exclude_unset=True)
        logger.info(f"update_company(company_id={company_id}) called with fields={list(update_fields.keys())}")
        try:
            update_fields["updated_at"] = datetime.now(timezone.utc)
            updated_storage = await self.storage.update_company(company_id, update_fields)
            if not updated_storage:
                logger.warning(f"Company not found for update: company_id={company_id}")
                return None
            company = Company(**updated_storage.model_dump())
            logger.info(f"update_company(company_id={company_id}) completed")
            return company
        except Exception as e:
            logger.error(f"Error in update_company(company_id={company_id}): {e}", exc_info=True)
            raise

    async def delete_company(self, company_id: str) -> bool:
        logger.info(f"delete_company(company_id={company_id}) called — soft delete")
        try:
            deleted = await self.storage.delete_company(company_id)
            if deleted:
                logger.info(f"Successfully soft-deleted company_id={company_id}")
            else:
                logger.warning(f"Company not found for soft-delete: company_id={company_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error in delete_company(company_id={company_id}): {e}", exc_info=True)
            raise
