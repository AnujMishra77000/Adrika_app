from app.db.models.academic import (
    Batch,
    BatchSubject,
    Branch,
    CompletedLecture,
    LectureSchedule,
    LectureScheduleStudent,
    Standard,
    StudentBatchEnrollment,
    StudentProfile,
    Subject,
    SubjectAcademicScope,
    TeacherBatchAssignment,
    TeacherProfile,
)
from app.db.models.assessment import (
    Assessment,
    AssessmentAssignment,
    AssessmentAttempt,
    AssessmentQuestion,
    AttemptAnswer,
    QuestionBank,
)
from app.db.models.attendance import AttendanceCorrection, AttendanceRecord
from app.db.models.audit import AuditLog, IdempotencyKey, OutboxEvent
from app.db.models.billing import FeeInvoice, FeeStructure, PaymentTransaction, StudentFeeStructureAssignment
from app.db.models.content import Banner, DailyThought, Notice, NoticeAttachment, NoticeRead, NoticeTarget
from app.db.models.doubt import Doubt, DoubtMessage
from app.db.models.homework import (
    Homework,
    HomeworkAttachment,
    HomeworkRead,
    HomeworkSubmission,
    HomeworkSubmissionAttachment,
    HomeworkTarget,
)
from app.db.models.notification import Notification, NotificationDelivery
from app.db.models.parent import ParentCommunicationPreference, ParentProfile, ParentStudentLink
from app.db.models.registration import RegistrationRequest
from app.db.models.results import Result, StudentProgressSnapshot
from app.db.models.user import DeviceRegistration, RefreshSession, Role, User, UserRole

__all__ = [
    "Assessment",
    "AssessmentAssignment",
    "AssessmentAttempt",
    "AssessmentQuestion",
    "AttemptAnswer",
    "AuditLog",
    "AttendanceCorrection",
    "AttendanceRecord",
    "Banner",
    "Batch",
    "BatchSubject",
    "Branch",
    "CompletedLecture",
    "LectureSchedule",
    "LectureScheduleStudent",
    "DailyThought",
    "DeviceRegistration",
    "Doubt",
    "DoubtMessage",
    "FeeInvoice",
    "FeeStructure",
    "Homework",
    "HomeworkAttachment",
    "HomeworkRead",
    "HomeworkSubmission",
    "HomeworkSubmissionAttachment",
    "HomeworkTarget",
    "IdempotencyKey",
    "Notice",
    "NoticeAttachment",
    "NoticeRead",
    "NoticeTarget",
    "Notification",
    "NotificationDelivery",
    "OutboxEvent",
    "ParentCommunicationPreference",
    "ParentProfile",
    "ParentStudentLink",
    "PaymentTransaction",
    "StudentFeeStructureAssignment",
    "QuestionBank",
    "RefreshSession",
    "RegistrationRequest",
    "Result",
    "Role",
    "Standard",
    "StudentBatchEnrollment",
    "StudentProfile",
    "StudentProgressSnapshot",
    "Subject",
    "SubjectAcademicScope",
    "TeacherBatchAssignment",
    "TeacherProfile",
    "User",
    "UserRole",
]
