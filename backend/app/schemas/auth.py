from pydantic import BaseModel, Field, model_validator


_PASSWORD_PATTERN = r"^[A-Za-z\d]{6,8}$"


def _has_letters_and_digits(value: str) -> bool:
    return any(ch.isalpha() for ch in value) and any(ch.isdigit() for ch in value)


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


class ForgotPasswordResetRequestDTO(BaseModel):
    phone: str = Field(min_length=10, max_length=15, pattern=r"^\d{10,15}$")
    new_password: str = Field(min_length=6, max_length=8, pattern=_PASSWORD_PATTERN)
    confirm_password: str = Field(min_length=6, max_length=8, pattern=_PASSWORD_PATTERN)
    role: str = Field(default="student", pattern=r"^(student|teacher)$")

    @model_validator(mode="after")
    def validate_password_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("new_password and confirm_password must match")
        if not _has_letters_and_digits(self.new_password):
            raise ValueError("password must include both letters and numbers")
        return self


class TokenPairDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginResponseDTO(BaseModel):
    tokens: TokenPairDTO
    user: dict
