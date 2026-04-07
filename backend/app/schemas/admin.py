from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class TargetDTO(BaseModel):
    target_type: str = Field(pattern="^(all|batch|student|teacher)$")
    target_id: str


class AdminStudentCreateDTO(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    password: str = Field(min_length=8)
    admission_no: str = Field(min_length=2, max_length=100)
    roll_no: str = Field(min_length=1, max_length=50)
    batch_id: str


class AdminStudentUpdateDTO(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|suspended)$")
    roll_no: str | None = Field(default=None, min_length=1, max_length=50)
    batch_id: str | None = None


class AdminBatchCreateDTO(BaseModel):
    standard_id: str
    name: str = Field(min_length=1, max_length=100)
    academic_year: int = Field(ge=2020, le=2100)


class AdminNoticeCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=5)
    priority: int = Field(default=0, ge=0, le=100)
    publish_at: datetime | None = None
    targets: list[TargetDTO]


class AdminHomeworkCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=5)
    subject_id: str
    due_date: date
    targets: list[TargetDTO]


class AdminAttendanceCorrectionCreateDTO(BaseModel):
    attendance_record_id: str
    reason: str = Field(min_length=3)


class AdminAttendanceCorrectionApproveDTO(BaseModel):
    status: str = Field(pattern="^(approved|rejected)$")
    new_attendance_status: str | None = Field(default=None, pattern="^(present|absent|late|leave)$")

    @model_validator(mode="after")
    def validate_attendance_status(self):
        if self.status == "approved" and self.new_attendance_status is None:
            raise ValueError("new_attendance_status is required when approving a correction")
        return self


class AdminAssessmentCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    subject_id: str
    assessment_type: str = Field(pattern="^(daily_practice|subject_practice|scheduled)$")
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    duration_sec: int = Field(ge=60, le=10800)
    attempt_limit: int = Field(default=1, ge=1, le=10)
    total_marks: float = Field(default=0, ge=0)
    targets: list[TargetDTO]

    @model_validator(mode="after")
    def validate_time_window(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        return self


class AdminResultPublishDTO(BaseModel):
    assessment_id: str
    student_id: str
    score: float = Field(ge=0)
    total_marks: float = Field(gt=0)
    rank: int | None = Field(default=None, ge=1)


class AdminDoubtUpdateDTO(BaseModel):
    status: str = Field(pattern="^(open|in_progress|resolved|closed)$")


class AdminNotificationCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2)
    notification_type: str = Field(pattern="^(notice|homework|test|result|doubt|system)$")
    targets: list[TargetDTO]


class AdminBannerCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    media_url: str = Field(min_length=3, max_length=1024)
    action_url: str | None = Field(default=None, max_length=1024)
    active_from: datetime
    active_to: datetime
    priority: int = Field(default=0, ge=0, le=100)
    is_popup: bool = False

    @model_validator(mode="after")
    def validate_active_window(self):
        if self.active_to <= self.active_from:
            raise ValueError("active_to must be greater than active_from")
        return self


class AdminBannerUpdateDTO(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    media_url: str | None = Field(default=None, min_length=3, max_length=1024)
    action_url: str | None = Field(default=None, max_length=1024)
    active_from: datetime | None = None
    active_to: datetime | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    is_popup: bool | None = None


class AdminDailyThoughtUpsertDTO(BaseModel):
    thought_date: date
    text: str = Field(min_length=5)
    is_active: bool = True


class AdminParentLinkCreateDTO(BaseModel):
    parent_user_id: str
    student_id: str
    relation_type: str = Field(default="guardian", pattern="^(father|mother|guardian|other)$")
    is_primary: bool = False


class AdminFeeInvoiceCreateDTO(BaseModel):
    student_id: str
    invoice_no: str = Field(min_length=1, max_length=64)
    period_label: str = Field(min_length=1, max_length=50)
    due_date: date
    amount: float = Field(gt=0)
    status: str = Field(default="pending", pattern="^(pending|paid|overdue|cancelled)$")


class AdminPaymentReconcileDTO(BaseModel):
    status: str = Field(pattern="^(pending|success|failed|refunded)$")
    paid_at: datetime | None = None
    external_ref: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
