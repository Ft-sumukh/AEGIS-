"""Pydantic schemas for SupportTicket and CustomerComplaint entities."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SeverityLevel, TicketPriority, TicketStatus


class SupportTicketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    customer_id: uuid.UUID | None
    category: str
    priority: TicketPriority
    status: TicketStatus
    summary: str
    created_at: datetime
    resolved_at: datetime | None
    ticket_metadata: dict[str, Any] = Field(default_factory=dict)


class CustomerComplaintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    company_id: uuid.UUID
    customer_id: uuid.UUID | None
    category: str
    severity: SeverityLevel
    summary: str
    created_at: datetime
    resolved_at: datetime | None
    complaint_metadata: dict[str, Any] = Field(default_factory=dict)
