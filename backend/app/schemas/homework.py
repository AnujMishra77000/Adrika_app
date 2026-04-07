from datetime import date

from pydantic import BaseModel


class HomeworkItemDTO(BaseModel):
    id: str
    title: str
    description: str
    subject_id: str
    due_date: date
    status: str
