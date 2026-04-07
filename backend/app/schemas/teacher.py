from pydantic import BaseModel, Field


class TeacherAddDoubtMessageDTO(BaseModel):
    message: str = Field(min_length=1)


class TeacherUpdateDoubtStatusDTO(BaseModel):
    status: str = Field(pattern="^(open|in_progress|resolved|closed)$")
