"""Pydantic schemas for Customer entities."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CustomerBase(BaseModel):
    company_id: uuid.UUID
    external_reference: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    region: str | None = Field(default=None, max_length=50)


class CustomerCreate(CustomerBase):
    pass


class CustomerRead(CustomerBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
