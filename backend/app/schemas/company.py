"""Pydantic schemas for Company entities."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CompanyStatus


class CompanyBase(BaseModel):
    name: str = Field(..., max_length=255, description="Organization name")
    slug: str = Field(..., max_length=100, description="Unique organizational slug")
    industry: str | None = Field(default=None, max_length=100)
    status: CompanyStatus = Field(default=CompanyStatus.ACTIVE)


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
