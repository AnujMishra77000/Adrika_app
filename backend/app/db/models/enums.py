from enum import StrEnum


class RoleCode(StrEnum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    PARENT = "parent"


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class NoticeStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class HomeworkStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    LEAVE = "leave"


class AssessmentType(StrEnum):
    DAILY_PRACTICE = "daily_practice"
    SUBJECT_PRACTICE = "subject_practice"
    SCHEDULED = "scheduled"


class AssessmentStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    COMPLETED = "completed"


class AttemptStatus(StrEnum):
    STARTED = "started"
    SUBMITTED = "submitted"
    AUTO_SUBMITTED = "auto_submitted"


class DoubtStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class NotificationType(StrEnum):
    NOTICE = "notice"
    HOMEWORK = "homework"
    TEST = "test"
    RESULT = "result"
    DOUBT = "doubt"
    SYSTEM = "system"


class DeliveryChannel(StrEnum):
    IN_APP = "in_app"
    PUSH = "push"
    WHATSAPP = "whatsapp"
