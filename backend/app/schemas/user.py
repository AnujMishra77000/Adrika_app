from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserDTO(BaseModel):
    id: str
    full_name: str
    email: EmailStr | None = None
    phone: str | None = None
    roles: list[str]
    created_at: datetime


class MeDTO(BaseModel):
    id: str
    full_name: str
    email: EmailStr | None
    phone: str | None
    roles: list[str]
