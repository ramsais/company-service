from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, description="Company name")
    industry: str = Field(..., min_length=1, description="Industry sector")
    website: Optional[str] = Field(default=None, description="Company website URL")
    location: Optional[str] = Field(default=None, description="Company location")
    is_active: bool = Field(default=True, description="Whether the company is active")


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, description="Company name")
    industry: Optional[str] = Field(default=None, min_length=1, description="Industry sector")
    website: Optional[str] = Field(default=None, description="Company website URL")
    location: Optional[str] = Field(default=None, description="Company location")
    is_active: Optional[bool] = Field(default=None, description="Whether the company is active")


class Company(CompanyBase):
    id: str = Field(..., description="Unique company identifier")
    created_at: datetime = Field(..., description="Timestamp when the company was created")
    updated_at: datetime = Field(..., description="Timestamp when the company was last updated")

    model_config = {"from_attributes": True}


class CompanyInStorage(CompanyBase):
    id: str
    created_at: datetime
    updated_at: datetime
