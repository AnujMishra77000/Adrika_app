def student_dashboard_key(student_id: str) -> str:
    return f"student:{student_id}:dashboard:v1"


def student_notices_key(student_id: str, limit: int, offset: int) -> str:
    return f"student:{student_id}:notices:{limit}:{offset}:v1"


def student_homework_key(student_id: str, limit: int, offset: int) -> str:
    return f"student:{student_id}:homework:{limit}:{offset}:v1"


def student_unread_notifications_key(user_id: str) -> str:
    return f"user:{user_id}:notif_unread:v1"


def student_content_key() -> str:
    return "student:content:v1"


def teacher_dashboard_key(teacher_id: str) -> str:
    return f"teacher:{teacher_id}:dashboard:v1"


def teacher_notices_key(teacher_id: str, limit: int, offset: int) -> str:
    return f"teacher:{teacher_id}:notices:{limit}:{offset}:v1"


def parent_dashboard_key(parent_id: str, student_id: str) -> str:
    return f"parent:{parent_id}:student:{student_id}:dashboard:v1"


def parent_notices_key(parent_id: str, student_id: str, limit: int, offset: int) -> str:
    return f"parent:{parent_id}:student:{student_id}:notices:{limit}:{offset}:v1"
