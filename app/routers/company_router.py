import logging

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user_role
from app.exceptions.custom import ResourceNotFoundException  # re-exported from app.exceptions.custom
from app.schemas.company import Company, CompanyCreate, CompanyUpdate
from app.services.company_service import CompanyService
from app.services.storage_service import CompanyStorage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/companies", tags=["Companies"])


def get_company_service() -> CompanyService:
    storage = CompanyStorage()
    return CompanyService(storage)


@router.get("/", response_model=list[Company])
async def list_companies(
        service: CompanyService = Depends(get_company_service),
        role: str = Depends(get_current_user_role),
):
    logger.info(f"GET /companies called, role={role}")
    try:
        result = await service.list_companies()
        logger.info(f"GET /companies completed, count={len(result)}, role={role}")
        return result
    except Exception as e:
        logger.error(f"Error in GET /companies: {e}", exc_info=True)
        raise


@router.get("/{company_id}", response_model=Company)
async def get_company(
        company_id: str,
        service: CompanyService = Depends(get_company_service),
        role: str = Depends(get_current_user_role),
):
    logger.info(f"GET /companies/{company_id} called, role={role}")
    try:
        company = await service.get_company(company_id)
        if not company:
            logger.warning(f"Company not found: company_id={company_id}")
            raise ResourceNotFoundException("Company", company_id)
        logger.info(f"GET /companies/{company_id} completed, role={role}")
        return company
    except Exception as e:
        logger.error(f"Error in GET /companies/{company_id}: {e}", exc_info=True)
        raise


@router.post("/", response_model=Company, status_code=201)
async def create_company(
        company_in: CompanyCreate,
        service: CompanyService = Depends(get_company_service),
        role: str = Depends(get_current_user_role),
):
    logger.info(f"POST /companies called, name={company_in.name}, role={role}")
    try:
        result = await service.create_company(company_in)
        logger.info(f"POST /companies completed, company_id={result.id}, role={role}")
        return result
    except Exception as e:
        logger.error(f"Error in POST /companies: {e}", exc_info=True)
        raise


@router.put("/{company_id}", response_model=Company)
async def update_company(
        company_id: str,
        company_in: CompanyUpdate,
        service: CompanyService = Depends(get_company_service),
        role: str = Depends(get_current_user_role),
):
    logger.info(
        f"PUT /companies/{company_id} called, fields={list(company_in.model_dump(exclude_unset=True).keys())}, role={role}")
    try:
        company = await service.update_company(company_id, company_in)
        if not company:
            logger.warning(f"Company not found for update: company_id={company_id}")
            raise ResourceNotFoundException("Company", company_id)
        logger.info(f"PUT /companies/{company_id} completed, role={role}")
        return company
    except Exception as e:
        logger.error(f"Error in PUT /companies/{company_id}: {e}", exc_info=True)
        raise


@router.delete("/{company_id}", status_code=204)
async def delete_company(
        company_id: str,
        service: CompanyService = Depends(get_company_service),
        role: str = Depends(get_current_user_role),
):
    logger.info(f"DELETE /companies/{company_id} called, role={role}")
    try:
        if role != "WRITE_USER":
            logger.warning(f"Unauthorized delete attempt: company_id={company_id}, role={role}")
            raise HTTPException(status_code=403, detail=f"{role} role is not allowed to delete a company")

        deleted = await service.delete_company(company_id)
        if not deleted:
            logger.warning(f"Company not found for delete: company_id={company_id}")
            raise ResourceNotFoundException("Company", company_id)
        logger.info(f"DELETE /companies/{company_id} soft-deleted successfully, role={role}")
        return None
    except Exception as e:
        logger.error(f"Error in DELETE /companies/{company_id}: {e}", exc_info=True)
        raise
