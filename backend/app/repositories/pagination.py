"""
Standardized Pagination Data Transfer Objects

Provides PageRequest and Page[T] DTOs to enforce unified pagination rules
across all repositories and API endpoints.
"""

import math
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageRequest(BaseModel):
    """
    Standard pagination request parameter container.
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    size: int = Field(default=50, ge=1, le=1000, description="Items per page")
    sort_by: str | None = Field(default=None, description="Column name to sort by")
    sort_order: Literal["ASC", "DESC"] = Field(
        default="ASC", description="Sort order direction"
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


class Page(BaseModel, Generic[T]):
    """
    Standardized paginated list response envelope.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    items: list[T]
    total_elements: int = Field(ge=0)
    page: int = Field(ge=1)
    size: int = Field(ge=1)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_previous: bool

    @classmethod
    def create(
        cls, items: list[T], total_elements: int, page_request: PageRequest
    ) -> "Page[T]":
        total_pages = (
            math.ceil(total_elements / page_request.size)
            if page_request.size > 0
            else 0
        )
        return cls(
            items=items,
            total_elements=total_elements,
            page=page_request.page,
            size=page_request.size,
            total_pages=total_pages,
            has_next=page_request.page < total_pages,
            has_previous=page_request.page > 1,
        )
