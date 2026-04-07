from pydantic import BaseModel


class StudentProfileDTO(BaseModel):
    student_id: str
    user_id: str
    full_name: str
    admission_no: str
    roll_no: str
    current_batch_id: str | None


class StudentDashboardDTO(BaseModel):
    unread_notifications: int
    pending_homework_count: int
    attendance_percentage: float
    upcoming_tests_count: int
