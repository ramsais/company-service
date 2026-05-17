import uuid
from datetime import datetime, timezone
from app.schemas.company import Company, CompanyCreate, CompanyUpdate, CompanyInStorage
from app.services.storage_service import CompanyStorage
from app.services.deal_service import DealServiceClient

class CompanyService:
    def __init__(self, storage: CompanyStorage, deal_client: DealServiceClient):
        self.storage = storage
        self.deal_client = deal_client

    async def list_companies(self) -> list[Company]:
        companies_storage = await self.storage.list_companies()
        result = []
        for c_storage in companies_storage:
            deals = await self.deal_client.get_deals_for_company(c_storage.id)
            result.append(Company(**c_storage.model_dump(), deals=deals))
        return result

    async def get_company(self, company_id: str) -> Company | None:
        c_storage = await self.storage.get_company(company_id)
        if not c_storage:
            return None
        deals = await self.deal_client.get_deals_for_company(company_id)
        return Company(**c_storage.model_dump(), deals=deals)

    async def create_company(self, company_in: CompanyCreate) -> Company:
        company_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        c_storage = CompanyInStorage(
            id=company_id, 
            created_at=now, 
            updated_at=now, 
            **company_in.model_dump()
        )
        await self.storage.create_company(c_storage)
        return Company(**c_storage.model_dump(), deals=[])

    async def update_company(self, company_id: str, company_in: CompanyUpdate) -> Company | None:
        update_data = company_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        updated_storage = await self.storage.update_company(
            company_id, 
            update_data
        )
        if not updated_storage:
            return None
        deals = await self.deal_client.get_deals_for_company(company_id)
        return Company(**updated_storage.model_dump(), deals=deals)

    async def delete_company(self, company_id: str) -> bool:
        return await self.storage.delete_company(company_id)
