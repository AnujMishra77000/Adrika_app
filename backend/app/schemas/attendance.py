from datetime import date

from pydantic import BaseModel


class AttendanceItemDTO(BaseModel):
    id: str
    attendance_date: date
    session_code: str
    status: str
    source: str


class AttendanceSummaryDTO(BaseModel):
    total_days: int
    present_days: int
    absent_days: int
    attendance_percentage: float
