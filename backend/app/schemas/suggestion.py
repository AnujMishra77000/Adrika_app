from pydantic import BaseModel, Field


class SuggestionMessageCreateDTO(BaseModel):
    message: str = Field(min_length=1, max_length=3000)
