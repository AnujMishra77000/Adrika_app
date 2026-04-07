from pydantic import BaseModel


class APIError(BaseModel):
    type: str
    title: str
    status: int
    code: str
    detail: str
    request_id: str | None = None


class PaginationMeta(BaseModel):
    limit: int
    offset: int
    total: int


class PageResponse(BaseModel):
    items: list
    meta: PaginationMeta
