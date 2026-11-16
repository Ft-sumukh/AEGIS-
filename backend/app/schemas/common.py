"""Common schemas and pagination primitives."""

from pydantic import BaseModel, ConfigDict, Field


class PaginationParams(BaseModel):
    """Query parameters for paginating collections."""

    limit: int = Field(default=50, ge=1, le=200, description="Maximum number of items to return")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")


class PaginatedResponse[T](BaseModel):
    """Standardized paginated list response envelope."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T] = Field(..., description="List of items for the requested page")
    total: int = Field(..., ge=0, description="Total count of available matching items")
    limit: int = Field(..., ge=1, description="Applied page limit")
    offset: int = Field(..., ge=0, description="Applied page offset")
