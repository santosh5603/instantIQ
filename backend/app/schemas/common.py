from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int

class APIResponse(BaseModel, Generic[T]):
    data: T
    meta: PaginationMeta | None = None

class SimpleResponse(BaseModel):
    data: dict
