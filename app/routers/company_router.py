from fastapi import APIRouter, Depends
from app.schemas.company import Company, CompanyCreate, CompanyUpdate
from app.services.company_service import CompanyService
from app.services.storage_service import CompanyStorage
from app.services.deal_service import DealServiceClient
from app.exceptions import ResourceNotFoundException
from app.auth import get_current_user_role

router = APIRouter(prefix="/companies", tags=["Companies"])


def get_company_service():
    storage = CompanyStorage()
    deal_client = DealServiceClient()
    return CompanyService(storage, deal_client)


@router.get("/", response_model=list[Company])
async def list_companies(
    service: CompanyService = Depends(get_company_service),
    role: str = Depends(get_current_user_role),
):
    return await service.list_companies()


@router.get("/{company_id}", response_model=Company)
async def get_company(
    company_id: str,
    service: CompanyService = Depends(get_company_service),
    role: str = Depends(get_current_user_role),
):
    company = await service.get_company(company_id)
    if not company:
        raise ResourceNotFoundException("Company", company_id)
    return company


@router.post("/", response_model=Company, status_code=201)
async def create_company(
    company_in: CompanyCreate,
    service: CompanyService = Depends(get_company_service),
    role: str = Depends(get_current_user_role),
):
    return await service.create_company(company_in)


@router.put("/{company_id}", response_model=Company)
async def update_company(
    company_id: str,
    company_in: CompanyUpdate,
    service: CompanyService = Depends(get_company_service),
    role: str = Depends(get_current_user_role),
):
    company = await service.update_company(company_id, company_in)
    if not company:
        raise ResourceNotFoundException("Company", company_id)
    return company


@router.delete("/{company_id}", status_code=204)
async def delete_company(
    company_id: str,
    service: CompanyService = Depends(get_company_service),
    role: str = Depends(get_current_user_role),
):
    if role != "WRITE_USER":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="WRITE_USER role required to delete a company")
    deleted = await service.delete_company(company_id)
    if not deleted:
        raise ResourceNotFoundException("Company", company_id)
    return None
