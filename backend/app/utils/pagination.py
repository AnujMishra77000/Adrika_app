from app.schemas.common import PaginationMeta


def build_meta(*, total: int, limit: int, offset: int) -> PaginationMeta:
    return PaginationMeta(total=total, limit=limit, offset=offset)
