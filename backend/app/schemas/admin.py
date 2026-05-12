from datetime import date, datetime
import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


_PASSWORD_POLICY_PATTERN = r"^[A-Za-z\d]{6,8}$"


def _has_letters_and_digits(value: str) -> bool:
    return any(ch.isalpha() for ch in value) and any(ch.isdigit() for ch in value)


class TargetDTO(BaseModel):
    target_type: str = Field(pattern="^(all|all_students|batch|student|teacher|grade)$")
    target_id: str


class AdminStudentCreateDTO(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str = Field(min_length=10, max_length=15, pattern=r"^\d{10,15}$")
    password: str | None = Field(default=None, min_length=6, max_length=8, pattern=_PASSWORD_POLICY_PATTERN)
    admission_no: str = Field(min_length=2, max_length=100)
    roll_no: str = Field(min_length=1, max_length=50)
    batch_id: str
    class_name: str | None = Field(default=None, max_length=50)
    stream: str | None = Field(default=None, pattern="^(science|commerce|common)$")
    parent_contact_number: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    school_details: str | None = Field(default=None, max_length=255)
    fee_structure_id: str | None = None
    manual_fee_amount: float | None = Field(default=None, ge=0)
    manual_fee_installment_count: int | None = Field(default=3, ge=1, le=24)
    negotiable_amount: float | None = Field(default=None, ge=0)
    installment_count: int | None = Field(default=None, ge=1, le=24)
    initial_fee_paid_amount: float | None = Field(default=None, ge=0)
    initial_fee_paid_on: date | None = None
    initial_fee_payment_mode: str = Field(default="cash", pattern="^(cash|upi|bank_transfer|card|cheque|other)$")
    initial_fee_reference_no: str | None = Field(default=None, max_length=120)
    initial_fee_note: str | None = Field(default=None, max_length=500)

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        normalized = "".join(ch for ch in value if ch.isdigit())
        if len(normalized) < 10 or len(normalized) > 15:
            raise ValueError("phone number must contain 10 to 15 digits")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _has_letters_and_digits(value):
            raise ValueError("password must include both letters and numbers")
        return value

    @model_validator(mode="after")
    def validate_initial_fee_flow(self):
        amount = float(self.initial_fee_paid_amount or 0)
        has_structure = bool(self.fee_structure_id)
        has_manual_fee = float(self.manual_fee_amount or 0) > 0
        if has_structure and has_manual_fee:
            raise ValueError("choose either fee_structure_id or manual_fee_amount, not both")
        if amount > 0 and not (has_structure or has_manual_fee):
            raise ValueError(
                "fee_structure_id or manual_fee_amount is required when initial_fee_paid_amount is greater than zero"
            )
        return self


class AdminStudentUpdateDTO(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    email: EmailStr | None = None
    phone: str | None = None
    status: str | None = Field(default=None, pattern="^(active|inactive|suspended)$")
    roll_no: str | None = Field(default=None, min_length=1, max_length=50)
    batch_id: str | None = None


class AdminStudentStatusUpdateDTO(BaseModel):
    status: str = Field(pattern="^(active|inactive|suspended)$")


class AdminStudentCredentialResetDTO(BaseModel):
    new_password: str | None = Field(default=None, min_length=6, max_length=8, pattern=_PASSWORD_POLICY_PATTERN)

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _has_letters_and_digits(value):
            raise ValueError("password must include both letters and numbers")
        return value


_TEACHING_SCOPE_PATTERN = r"^(6|7|8|9|10)-common|(11|12)-(science|commerce)$"


class AdminTeacherCreateDTO(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=10, max_length=15, pattern=r"^\d{10,15}$")
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=8, pattern=_PASSWORD_POLICY_PATTERN)
    employee_code: str | None = Field(default=None, min_length=2, max_length=50)
    designation: str | None = Field(default=None, max_length=100)
    age: int | None = Field(default=None, ge=18, le=90)
    gender: str | None = Field(default=None, max_length=20)
    qualification: str | None = Field(default=None, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    school_college: str | None = Field(default=None, max_length=255)
    teaching_scopes: list[str] = Field(min_length=1, max_length=20)
    address: str | None = Field(default=None, max_length=500)
    hourly_salary_rate: float = Field(default=0, ge=0)

    @field_validator("phone")
    @classmethod
    def normalize_teacher_phone(cls, value: str) -> str:
        normalized = "".join(ch for ch in value if ch.isdigit())
        if len(normalized) < 10 or len(normalized) > 15:
            raise ValueError("phone number must contain 10 to 15 digits")
        return normalized

    @field_validator("password")
    @classmethod
    def validate_teacher_password_strength(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _has_letters_and_digits(value):
            raise ValueError("password must include both letters and numbers")
        return value

    @field_validator("teaching_scopes")
    @classmethod
    def validate_teaching_scopes(cls, scopes: list[str]) -> list[str]:
        normalized: list[str] = []
        for scope in scopes:
            token = (scope or "").strip().lower()
            if not token:
                continue
            if not re.match(_TEACHING_SCOPE_PATTERN, token):
                raise ValueError(f"invalid teaching scope: {scope}")
            if token not in normalized:
                normalized.append(token)
        if not normalized:
            raise ValueError("at least one valid teaching scope is required")
        return normalized


class AdminTeacherStatusUpdateDTO(BaseModel):
    status: str = Field(pattern="^(active|inactive|suspended)$")


class AdminTeacherCredentialResetDTO(BaseModel):
    new_password: str | None = Field(default=None, min_length=6, max_length=8, pattern=_PASSWORD_POLICY_PATTERN)

    @field_validator("new_password")
    @classmethod
    def validate_teacher_new_password_strength(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not _has_letters_and_digits(value):
            raise ValueError("password must include both letters and numbers")
        return value


class AdminBatchCreateDTO(BaseModel):
    standard_id: str
    name: str = Field(min_length=1, max_length=100)
    academic_year: int = Field(ge=2020, le=2100)




class AdminStandardCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    branch_id: str | None = None


class AdminSubjectCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    code: str | None = Field(default=None, min_length=2, max_length=50)
    class_level: int = Field(ge=6, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    estimated_hours: int | None = Field(default=None, ge=1, le=5000)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.class_level <= 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10 and below")
        if self.class_level in {11, 12} and self.stream is None:
            raise ValueError("stream is required for class 11 and 12")
        return self


class AdminSubjectEstimateUpsertDTO(BaseModel):
    class_level: int = Field(ge=6, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    estimated_hours: int = Field(ge=1, le=5000)

    @model_validator(mode="after")
    def validate_scope(self):
        if self.class_level <= 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10 and below")
        if self.class_level in {11, 12} and self.stream is None:
            raise ValueError("stream is required for class 11 and 12")
        return self


class AdminNoticeCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=5)
    priority: int = Field(default=0, ge=0, le=100)
    publish_at: datetime | None = None
    targets: list[TargetDTO]


class AdminHomeworkCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    subject_id: str
    due_at: datetime | None = None
    due_date: date | None = None
    targets: list[TargetDTO]

    @model_validator(mode="after")
    def validate_due_window(self):
        if self.due_at is None and self.due_date is None:
            raise ValueError("either due_at or due_date is required")
        return self


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
    assessment_type: str = Field(
        pattern="^(daily_practice|subject_practice|scheduled|practice_test|online_test|practice|online)$"
    )
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


class AdminQuestionOptionDTO(BaseModel):
    key: str = Field(min_length=1, max_length=4)
    text: str = Field(min_length=1, max_length=500)


class AdminQuestionBankCreateDTO(BaseModel):
    class_level: int = Field(ge=6, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    subject_id: str
    topic: str = Field(min_length=2, max_length=150)
    prompt: str = Field(min_length=5, max_length=2000)
    options: list[AdminQuestionOptionDTO] = Field(min_length=2, max_length=6)
    correct_option_key: str = Field(min_length=1, max_length=4)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    default_marks: float = Field(default=1, gt=0, le=100)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_question(self):
        if self.class_level <= 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10 and below")
        if self.class_level in {11, 12} and self.stream is None:
            raise ValueError("stream is required for class 11 and 12")

        keys = [item.key.strip().upper() for item in self.options]
        if len(keys) != len(set(keys)):
            raise ValueError("option keys must be unique")

        if self.correct_option_key.strip().upper() not in keys:
            raise ValueError("correct_option_key must match one of the option keys")

        return self


class AdminQuestionBankUpdateDTO(BaseModel):
    class_level: int | None = Field(default=None, ge=6, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    subject_id: str | None = None
    topic: str | None = Field(default=None, min_length=2, max_length=150)
    prompt: str | None = Field(default=None, min_length=5, max_length=2000)
    options: list[AdminQuestionOptionDTO] | None = Field(default=None, min_length=2, max_length=6)
    correct_option_key: str | None = Field(default=None, min_length=1, max_length=4)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    default_marks: float | None = Field(default=None, gt=0, le=100)
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_question(self):
        if self.class_level is not None and self.class_level <= 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10 and below")

        if self.options is not None:
            keys = [item.key.strip().upper() for item in self.options]
            if len(keys) != len(set(keys)):
                raise ValueError("option keys must be unique")
            if self.correct_option_key is not None and self.correct_option_key.strip().upper() not in keys:
                raise ValueError("correct_option_key must match one of the option keys")

        return self


class AdminAssessmentQuestionSelectDTO(BaseModel):
    question_id: str
    marks: float = Field(gt=0, le=100)
    negative_marks: float = Field(default=0, ge=0, le=100)


class AdminAssessmentBuildDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = None
    class_level: int = Field(ge=6, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    subject_id: str
    topic: str | None = Field(default=None, min_length=2, max_length=150)
    assessment_type: str = Field(
        default="scheduled",
        pattern="^(daily_practice|subject_practice|scheduled|practice_test|online_test|practice|online)$",
    )
    duration_minutes: int = Field(ge=5, le=240)
    attempt_limit: int = Field(default=1, ge=1, le=5)
    passing_marks: float = Field(ge=0)
    questions: list[AdminAssessmentQuestionSelectDTO] = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def validate_assessment_build(self):
        if self.class_level <= 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10 and below")
        if self.class_level in {11, 12} and self.stream is None:
            raise ValueError("stream is required for class 11 and 12")

        total_marks = sum(item.marks for item in self.questions)
        if self.passing_marks > total_marks:
            raise ValueError("passing_marks cannot exceed total marks")
        return self


class AdminAssessmentAssignDTO(BaseModel):
    starts_at: datetime
    ends_at: datetime
    targets: list[TargetDTO] | None = None
    publish: bool = True
    send_notification: bool = True

    @model_validator(mode="after")
    def validate_window(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be greater than starts_at")
        return self


class AdminResultPublishDTO(BaseModel):
    assessment_id: str
    student_id: str
    score: float = Field(ge=0)
    total_marks: float = Field(gt=0)
    rank: int | None = Field(default=None, ge=1)


class AdminResultWhatsappDTO(BaseModel):
    phone: str | None = Field(default=None, max_length=24)
    message: str | None = Field(default=None, max_length=1200)


class AdminDoubtUpdateDTO(BaseModel):
    status: str = Field(pattern="^(open|in_progress|resolved|closed)$")


class NotificationAttachmentDTO(BaseModel):
    file_name: str = Field(min_length=1, max_length=255)
    file_url: str = Field(min_length=1, max_length=1024)
    content_type: str = Field(min_length=3, max_length=100)
    file_size: int = Field(ge=1, le=20_000_000)


class AdminNotificationCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2)
    notification_type: str = Field(pattern="^(notice|homework|test|result|doubt|system)$")
    targets: list[TargetDTO]
    attachments: list[NotificationAttachmentDTO] = Field(default_factory=list, max_length=10)


class AdminBannerCreateDTO(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    media_url: str = Field(min_length=3, max_length=1024)
    action_url: str | None = Field(default=None, max_length=1024)
    active_from: datetime
    active_to: datetime
    priority: int = Field(default=0, ge=0, le=100)
    is_popup: bool = False
    is_active: bool = True

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
    is_active: bool | None = None


class AdminDailyThoughtUpsertDTO(BaseModel):
    thought_date: date
    text: str = Field(min_length=5)
    is_active: bool = True


class AdminParentLinkCreateDTO(BaseModel):
    parent_user_id: str
    student_id: str
    relation_type: str = Field(default="guardian", pattern="^(father|mother|guardian|other)$")
    is_primary: bool = False


class AdminStudentEnquiryCreateDTO(BaseModel):
    student_name: str = Field(min_length=2, max_length=255)
    class_level: int = Field(ge=6, le=12)
    previous_class: str | None = Field(default=None, max_length=50)
    previous_percentage: float | None = Field(default=None, ge=0, le=100)
    school_name: str | None = Field(default=None, max_length=255)
    language: str = Field(default="english", pattern="^(hindi|english)$")
    contact_number: str = Field(min_length=8, max_length=20)
    parent_contact_number: str = Field(min_length=8, max_length=20)
    follow_up_at: datetime | None = None
    batch_id: str | None = None

    fee_class_level: int = Field(ge=6, le=12)
    fee_stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    fee_structure_id: str | None = None
    manual_fee_amount: float | None = Field(default=None, ge=0)
    manual_fee_installment_count: int | None = Field(default=3, ge=1, le=24)
    negotiable_amount: float | None = Field(default=None, ge=0)
    installment_count: int | None = Field(default=None, ge=1, le=24)
    initial_fee_paid_amount: float | None = Field(default=None, ge=0)
    initial_fee_paid_on: date | None = None
    initial_fee_payment_mode: str = Field(
        default="cash", pattern="^(cash|upi|bank_transfer|card|cheque|other)$"
    )
    initial_fee_reference_no: str | None = Field(default=None, max_length=120)
    initial_fee_note: str | None = Field(default=None, max_length=500)
    status: str = Field(default="follow_up", pattern="^(interested|follow_up|confirmed|not_interested)$")
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_fee_scope(self):
        if self.fee_class_level <= 10 and self.fee_stream is not None:
            raise ValueError("fee_stream is not allowed for class 10 and below")
        if self.fee_class_level in {11, 12} and self.fee_stream is None:
            raise ValueError("fee_stream is required for class 11 and 12")
        has_structure = bool(self.fee_structure_id)
        has_manual_fee = float(self.manual_fee_amount or 0) > 0
        if has_structure and has_manual_fee:
            raise ValueError("choose either fee_structure_id or manual_fee_amount, not both")
        if float(self.initial_fee_paid_amount or 0) > 0 and not (has_structure or has_manual_fee):
            raise ValueError(
                "fee_structure_id or manual_fee_amount is required when initial_fee_paid_amount is greater than zero"
            )
        return self


class AdminStudentEnquiryUpdateDTO(BaseModel):
    student_name: str | None = Field(default=None, min_length=2, max_length=255)
    class_level: int | None = Field(default=None, ge=6, le=12)
    previous_class: str | None = Field(default=None, max_length=50)
    previous_percentage: float | None = Field(default=None, ge=0, le=100)
    school_name: str | None = Field(default=None, max_length=255)
    language: str | None = Field(default=None, pattern="^(hindi|english)$")
    contact_number: str | None = Field(default=None, min_length=8, max_length=20)
    parent_contact_number: str | None = Field(default=None, min_length=8, max_length=20)
    follow_up_at: datetime | None = None
    batch_id: str | None = None

    fee_class_level: int | None = Field(default=None, ge=6, le=12)
    fee_stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    fee_structure_id: str | None = None
    manual_fee_amount: float | None = Field(default=None, ge=0)
    manual_fee_installment_count: int | None = Field(default=None, ge=1, le=24)
    negotiable_amount: float | None = Field(default=None, ge=0)
    installment_count: int | None = Field(default=None, ge=1, le=24)
    initial_fee_paid_amount: float | None = Field(default=None, ge=0)
    initial_fee_paid_on: date | None = None
    initial_fee_payment_mode: str | None = Field(
        default=None, pattern="^(cash|upi|bank_transfer|card|cheque|other)$"
    )
    initial_fee_reference_no: str | None = Field(default=None, max_length=120)
    initial_fee_note: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, pattern="^(interested|follow_up|confirmed|not_interested)$")
    notes: str | None = Field(default=None, max_length=1000)
    status_note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_fee_choice(self):
        has_structure = bool(self.fee_structure_id)
        has_manual_fee = self.manual_fee_amount is not None and float(self.manual_fee_amount) > 0
        if has_structure and has_manual_fee:
            raise ValueError("choose either fee_structure_id or manual_fee_amount, not both")
        return self



class AdminFeeStructureCreateDTO(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    class_level: int = Field(ge=6, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    total_amount: float = Field(gt=0)
    installment_count: int = Field(default=1, ge=1, le=24)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_class_stream_rules(self):
        if self.class_level <= 10 and self.stream is not None:
            raise ValueError("stream is not allowed for class 10 and below")
        if self.class_level in {11, 12} and self.stream is None:
            raise ValueError("stream is required for class 11 and 12")
        return self


class AdminFeeStructureUpdateDTO(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    class_level: int | None = Field(default=None, ge=6, le=12)
    stream: str | None = Field(default=None, pattern="^(science|commerce)$")
    total_amount: float | None = Field(default=None, gt=0)
    installment_count: int | None = Field(default=None, ge=1, le=24)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class AdminStudentFeeStructureAssignDTO(BaseModel):
    fee_structure_id: str


class AdminStudentFeePaymentCreateDTO(BaseModel):
    amount: float = Field(gt=0)
    paid_on: date = Field(default_factory=date.today)
    payment_mode: str = Field(default="cash", pattern="^(cash|upi|bank_transfer|card|cheque|other)$")
    reference_no: str | None = Field(default=None, max_length=120)
    note: str | None = Field(default=None, max_length=500)
    period_label: str | None = Field(default=None, max_length=50)
    installment_no: int | None = Field(default=None, ge=1, le=24)


class AdminStudentFeeReceiptWhatsappDTO(BaseModel):
    phone: str | None = Field(default=None, max_length=24)
    message: str | None = Field(default=None, max_length=600)


class AdminFeeOverdueReminderDTO(BaseModel):
    student_ids: list[str] | None = Field(default=None, max_length=200)
    message: str | None = Field(default=None, max_length=500)
