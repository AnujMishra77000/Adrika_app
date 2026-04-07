from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cache.redis_client import get_redis
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models.academic import (
    Batch,
    Branch,
    Standard,
    StudentProfile,
    Subject,
    TeacherBatchAssignment,
    TeacherProfile,
)
from app.db.models.assessment import Assessment, AssessmentAssignment
from app.db.models.attendance import AttendanceRecord
from app.db.models.billing import FeeInvoice, PaymentTransaction
from app.db.models.content import Banner, DailyThought, Notice, NoticeTarget
from app.db.models.doubt import Doubt
from app.db.models.enums import (
    AssessmentStatus,
    AssessmentType,
    AttendanceStatus,
    HomeworkStatus,
    NoticeStatus,
    NotificationType,
    RoleCode,
)
from app.db.models.homework import Homework, HomeworkTarget
from app.db.models.notification import Notification
from app.db.models.parent import ParentProfile, ParentStudentLink
from app.db.models.results import Result, StudentProgressSnapshot
from app.db.models.user import Role, User, UserRole
from app.db.session import get_db_session
from app.main import app


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None):
        self.store[key] = value

    async def delete(self, *keys: str):
        for key in keys:
            self.store.pop(key, None)


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_maker() as session:
        student_role = Role(code=RoleCode.STUDENT, name="Student")
        teacher_role = Role(code=RoleCode.TEACHER, name="Teacher")
        parent_role = Role(code=RoleCode.PARENT, name="Parent")
        admin_role = Role(code=RoleCode.ADMIN, name="Admin")
        session.add_all([student_role, teacher_role, parent_role, admin_role])
        await session.flush()

        branch = Branch(code="MAIN", name="Main")
        session.add(branch)
        await session.flush()

        standard = Standard(branch_id=branch.id, name="Class 10")
        session.add(standard)
        await session.flush()

        batch = Batch(standard_id=standard.id, name="A", academic_year=2026)
        subject = Subject(code="MATH", name="Math")
        session.add_all([batch, subject])
        await session.flush()

        student_user = User(
            full_name="Test Student",
            email="student@test.local",
            phone="9000000001",
            password_hash=get_password_hash("Student@123"),
        )
        teacher_user = User(
            full_name="Test Teacher",
            email="teacher@test.local",
            phone="9000000003",
            password_hash=get_password_hash("Teacher@123"),
        )
        parent_user = User(
            full_name="Test Parent",
            email="parent@test.local",
            phone="9000000004",
            password_hash=get_password_hash("Parent@123"),
        )
        admin_user = User(
            full_name="Test Admin",
            email="admin@test.local",
            phone="9000000002",
            password_hash=get_password_hash("Admin@123"),
        )
        session.add_all([student_user, teacher_user, parent_user, admin_user])
        await session.flush()

        session.add_all(
            [
                UserRole(user_id=student_user.id, role_id=student_role.id),
                UserRole(user_id=teacher_user.id, role_id=teacher_role.id),
                UserRole(user_id=parent_user.id, role_id=parent_role.id),
                UserRole(user_id=admin_user.id, role_id=admin_role.id),
            ]
        )

        student_profile = StudentProfile(
            user_id=student_user.id,
            admission_no="ADM-001",
            roll_no="10A-1",
            current_batch_id=batch.id,
        )
        teacher_profile = TeacherProfile(
            user_id=teacher_user.id,
            employee_code="EMP-001",
            designation="Math Faculty",
        )
        parent_profile = ParentProfile(user_id=parent_user.id)
        session.add_all([student_profile, teacher_profile, parent_profile])
        await session.flush()

        session.add_all(
            [
                TeacherBatchAssignment(
                    teacher_id=teacher_profile.id,
                    batch_id=batch.id,
                    subject_id=subject.id,
                ),
                ParentStudentLink(
                    parent_id=parent_profile.id,
                    student_id=student_profile.id,
                    relation_type="father",
                    is_primary=True,
                    is_active=True,
                ),
            ]
        )

        notice = Notice(
            title="Test Notice",
            body="This is a notice",
            status=NoticeStatus.PUBLISHED,
            priority=1,
            created_by=admin_user.id,
        )
        teacher_notice = Notice(
            title="Teacher Brief",
            body="Please review today's lecture plan.",
            status=NoticeStatus.PUBLISHED,
            priority=2,
            created_by=admin_user.id,
        )
        session.add_all([notice, teacher_notice])
        await session.flush()
        session.add(NoticeTarget(notice_id=notice.id, target_type="all", target_id="all"))
        session.add_all(
            [
                NoticeTarget(notice_id=teacher_notice.id, target_type="teacher", target_id=teacher_profile.id),
                NoticeTarget(notice_id=teacher_notice.id, target_type="batch", target_id=batch.id),
            ]
        )

        homework = Homework(
            title="Quadratic Worksheet",
            description="Solve problems 1-10",
            subject_id=subject.id,
            due_date=date.today() + timedelta(days=2),
            status=HomeworkStatus.PUBLISHED,
            created_by=admin_user.id,
        )
        session.add(homework)
        await session.flush()
        session.add(HomeworkTarget(homework_id=homework.id, target_type="batch", target_id=batch.id))

        assessment = Assessment(
            title="Math Practice Test",
            description="Chapter practice",
            subject_id=subject.id,
            assessment_type=AssessmentType.DAILY_PRACTICE,
            status=AssessmentStatus.PUBLISHED,
            starts_at=datetime.now(UTC) + timedelta(hours=2),
            ends_at=datetime.now(UTC) + timedelta(days=1),
            duration_sec=1800,
            attempt_limit=1,
            total_marks=20,
        )
        session.add(assessment)
        await session.flush()
        session.add(AssessmentAssignment(assessment_id=assessment.id, target_type="batch", target_id=batch.id))

        session.add(
            Doubt(
                student_id=student_profile.id,
                subject_id=subject.id,
                topic="Factorization",
                description="Need help with x^2 + 5x + 6",
            )
        )

        session.add_all(
            [
                AttendanceRecord(
                    student_id=student_profile.id,
                    batch_id=batch.id,
                    attendance_date=date.today() - timedelta(days=1),
                    session_code="day",
                    status=AttendanceStatus.PRESENT,
                    source="biometric",
                    marked_at=datetime.now(UTC) - timedelta(days=1),
                ),
                AttendanceRecord(
                    student_id=student_profile.id,
                    batch_id=batch.id,
                    attendance_date=date.today() - timedelta(days=2),
                    session_code="day",
                    status=AttendanceStatus.ABSENT,
                    source="manual",
                    marked_at=datetime.now(UTC) - timedelta(days=2),
                ),
            ]
        )

        session.add(
            Result(
                assessment_id=assessment.id,
                student_id=student_profile.id,
                score=17,
                total_marks=20,
                rank=3,
                published_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        session.add(
            StudentProgressSnapshot(
                student_id=student_profile.id,
                period_type="monthly",
                period_start=date.today().replace(day=1),
                metrics={"average_score": 85, "attendance_pct": 90.0},
            )
        )

        invoice = FeeInvoice(
            student_id=student_profile.id,
            invoice_no="INV-001",
            period_label="Apr-2026",
            due_date=date.today() + timedelta(days=10),
            amount=2500,
            status="pending",
            paid_at=None,
        )
        session.add(invoice)
        await session.flush()

        session.add(
            PaymentTransaction(
                invoice_id=invoice.id,
                student_id=student_profile.id,
                provider="razorpay",
                external_ref="pay_001",
                amount=1200,
                status="success",
                paid_at=datetime.now(UTC) - timedelta(days=5),
                metadata_json={"mode": "upi"},
            )
        )

        session.add_all(
            [
                Notification(
                    recipient_user_id=student_user.id,
                    notification_type=NotificationType.SYSTEM,
                    title="Student Welcome",
                    body="Student dashboard is ready.",
                    is_read=False,
                ),
                Notification(
                    recipient_user_id=teacher_user.id,
                    notification_type=NotificationType.SYSTEM,
                    title="Teacher Welcome",
                    body="Teacher dashboard is ready.",
                    is_read=False,
                ),
                Notification(
                    recipient_user_id=parent_user.id,
                    notification_type=NotificationType.SYSTEM,
                    title="Parent Welcome",
                    body="Parent dashboard is ready.",
                    is_read=False,
                ),
            ]
        )

        now = datetime.now(UTC)
        session.add(
            Banner(
                title="Welcome Banner",
                media_url="https://cdn.adr.local/welcome.png",
                action_url="https://adr.local",
                active_from=now - timedelta(days=1),
                active_to=now + timedelta(days=3),
                priority=5,
                is_popup=False,
            )
        )
        session.add(
            DailyThought(
                thought_date=date.today(),
                text="Focus on progress, not perfection.",
                is_active=True,
            )
        )
        await session.commit()

        yield session

    await engine.dispose()


@pytest.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _get_redis_override() -> AsyncGenerator[FakeRedis, None]:
        yield FakeRedis()

    app.dependency_overrides[get_db_session] = _get_db_override
    app.dependency_overrides[get_redis] = _get_redis_override

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client

    app.dependency_overrides.clear()


async def login_token(client: AsyncClient, identifier: str, password: str, device_id: str) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": identifier,
            "password": password,
            "device": {
                "device_id": device_id,
                "platform": "android",
                "app_version": "1.0.0",
            },
        },
    )
    assert response.status_code == 200
    return response.json()["tokens"]["access_token"]
