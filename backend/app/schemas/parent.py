from pydantic import BaseModel, Field


class ParentUpdatePreferenceDTO(BaseModel):
    in_app_enabled: bool = True
    push_enabled: bool = True
    whatsapp_enabled: bool = False
    fee_reminders_enabled: bool = True
    preferred_language: str = Field(default="en", min_length=2, max_length=10)
