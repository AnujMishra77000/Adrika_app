from pydantic import BaseModel, Field


class DeviceInfoDTO(BaseModel):
    device_id: str = Field(min_length=3, max_length=255)
    platform: str = Field(min_length=2, max_length=20)
    app_version: str | None = None


class LoginRequestDTO(BaseModel):
    identifier: str
    password: str
    device: DeviceInfoDTO


class RefreshRequestDTO(BaseModel):
    refresh_token: str


class TokenPairDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponseDTO(BaseModel):
    tokens: TokenPairDTO
    user: dict
