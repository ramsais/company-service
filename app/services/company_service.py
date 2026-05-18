import uuid
import logging
from datetime import datetime, timezone
from app.schemas.company import Company, CompanyCreate, CompanyUpdate, CompanyInStorage
from app.services.storage_service import CompanyStorage
from app.services.deal_service import DealServiceClient

logger = logging.getLogger(__name__)

class CompanyService:
    def __init__(self, storage: CompanyStorage, deal_client: DealServiceClient):
        self.storage = storage
        self.deal_client = deal_client
        logger.info(f"CompanyService initialized with storage_file_path={storage.file_path}")

    async def list_companies(self) -> list[Company]:
        logger.info("list_companies() called")
        try:
            companies_storage = await self.storage.list_companies()
            logger.info(f"Retrieved {len(companies_storage)} companies from storage")

            result = []
            for c_storage in companies_storage:
                logger.debug(f"Fetching deals for company_id={c_storage.id}")
                deals = await self.deal_client.get_deals_for_company(c_storage.id)
                company = Company(**c_storage.model_dump(), deals=deals)
                result.append(company)
                logger.debug(f"Added company {c_storage.id} with {len(deals)} deals")

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

            logger.debug(f"Retrieved company from storage for company_id={company_id}")
            deals = await self.deal_client.get_deals_for_company(company_id)
            logger.info(f"Fetched {len(deals)} deals for company_id={company_id}")

            company = Company(**c_storage.model_dump(), deals=deals)
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
            logger.debug(f"Generated company_id={company_id}, now={now}")

            c_storage = CompanyInStorage(
                id=company_id,
                created_at=now,
                updated_at=now,
                **company_in.model_dump()
            )
            logger.debug(f"Created CompanyInStorage object for company_id={company_id}")

            await self.storage.create_company(c_storage)
            logger.info(f"Successfully persisted company_id={company_id} to storage")

            company = Company(**c_storage.model_dump(), deals=[])
            logger.info(f"create_company() completed for company_id={company_id}")
            return company
        except Exception as e:
            logger.error(f"Error in create_company(): {e}", exc_info=True)
            raise

    async def update_company(self, company_id: str, company_in: CompanyUpdate) -> Company | None:
        logger.info(f"update_company(company_id={company_id}) called with data={company_in.model_dump(exclude_unset=True)}")
        try:
            update_data = company_in.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.now(timezone.utc)
            logger.debug(f"Update data prepared: {update_data}")

            updated_storage = await self.storage.update_company(company_id, update_data)
            if not updated_storage:
                logger.warning(f"Company not found for update: company_id={company_id}")
                return None

            logger.info(f"Company updated in storage: company_id={company_id}")
            deals = await self.deal_client.get_deals_for_company(company_id)
            logger.info(f"Fetched {len(deals)} deals for company_id={company_id}")

            company = Company(**updated_storage.model_dump(), deals=deals)
            logger.info(f"update_company(company_id={company_id}) completed")
            return company
        except Exception as e:
            logger.error(f"Error in update_company(company_id={company_id}): {e}", exc_info=True)
            raise

    async def delete_company(self, company_id: str) -> bool:
        logger.info(f"delete_company(company_id={company_id}) called")
        try:
            deleted = await self.storage.delete_company(company_id)
            if deleted:
                logger.info(f"Successfully deleted company_id={company_id}")
            else:
                logger.warning(f"Company not found for deletion: company_id={company_id}")
            return deleted
        except Exception as e:
            logger.error(f"Error in delete_company(company_id={company_id}): {e}", exc_info=True)
            raise

