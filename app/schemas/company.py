from pydantic import BaseModel, Field
from datetime import datetime

class Deal(BaseModel):
    id: str
    title: str
    amount: float
    status: str

class CompanyBase(BaseModel):
    name: str
    industry: str
    website: str | None = None
    location: str | None = None
    is_active: bool = True

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(CompanyBase):
    name: str | None = None
    industry: str | None = None
    is_active: bool | None = None

class Company(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime
    deals: list[Deal] = Field(default_factory=list)

class CompanyInStorage(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime
