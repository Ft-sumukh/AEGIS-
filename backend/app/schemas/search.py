"""Pydantic schemas for global operational search."""

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """Normalized search result item across operational domains."""

    id: str
    type: str  # incident, investigation, system, anomaly
    title: str
    subtitle: str | None = None
    status: str | None = None
    severity: str | None = None
    url: str


class GlobalSearchResponse(BaseModel):
    """Grouped search response for fast operator navigation."""

    query: str
    total: int
    results: list[SearchResultItem] = Field(default_factory=list)
