import re

from pydantic import BaseModel, Field, field_validator, model_validator


_PHONE_PATTERN = re.compile(r"^[0-9]{10,15}$")


class StudentRegistrationDTO(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    class_name: str = Field(min_length=1, max_length=50)
    stream: str = Field(min_length=3, max_length=20)
    contact_number: str
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    parent_contact_number: str
    address: str = Field(min_length=5, max_length=500)
    school_details: str = Field(min_length=2, max_length=255)

    @field_validator("stream")
    @classmethod
    def normalize_stream(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"science", "commerce", "common"}:
            raise ValueError("stream must be one of: science, commerce, common")
        return normalized

    @field_validator("contact_number", "parent_contact_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = re.sub(r"\D", "", value)
        if not _PHONE_PATTERN.match(normalized):
            raise ValueError("phone number must contain 10 to 15 digits")
        return normalized

    @model_validator(mode="after")
    def validate_password_and_stream(self):
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password must match")

        class_num_match = re.search(r"\d{1,2}", self.class_name)
        class_num = int(class_num_match.group()) if class_num_match else None

        if class_num is not None and class_num <= 10 and self.stream != "common":
            raise ValueError("stream must be common for class 10 and below")

        if class_num is not None and class_num > 10 and self.stream == "common":
            raise ValueError("stream must be science or commerce for class 11 and above")

        return self


class TeacherRegistrationDTO(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    age: int = Field(ge=18, le=90)
    gender: str = Field(min_length=4, max_length=20)
    qualification: str = Field(min_length=2, max_length=255)
    specialization: str = Field(min_length=2, max_length=255)
    school_college: str | None = Field(default=None, max_length=255)
    contact_number: str
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    address: str = Field(min_length=5, max_length=500)

    @field_validator("gender")
    @classmethod
    def normalize_gender(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"male", "female", "other"}:
            raise ValueError("gender must be one of: male, female, other")
        return normalized

    @field_validator("contact_number")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        normalized = re.sub(r"\D", "", value)
        if not _PHONE_PATTERN.match(normalized):
            raise ValueError("phone number must contain 10 to 15 digits")
        return normalized

    @model_validator(mode="after")
    def validate_password(self):
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password must match")
        return self


class RegistrationResponseDTO(BaseModel):
    request_id: str
    user_id: str
    status: str
    message: str


class AdminRegistrationDecisionDTO(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=500)
