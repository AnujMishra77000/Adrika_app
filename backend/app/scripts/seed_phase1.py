import asyncio
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select

from app.core.security import get_password_hash
from app.db.models.academic import (
    Batch,
    Branch,
    Standard,
    StudentBatchEnrollment,
    StudentProfile,
    Subject,
    TeacherBatchAssignment,
    TeacherProfile,
)
from app.db.models.assessment import Assessment, AssessmentAssignment
from app.db.models.attendance import AttendanceRecord
from app.db.models.billing import FeeInvoice, PaymentTransaction
from app.db.models.content import DailyThought, Notice, NoticeTarget
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
from app.db.session import AsyncSessionLocal


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        for table in [
            UserRole,
            ParentStudentLink,
            ParentProfile,
            TeacherBatchAssignment,
            StudentBatchEnrollment,
            PaymentTransaction,
            FeeInvoice,
            Notification,
            AttendanceRecord,
            HomeworkTarget,
            Homework,
            NoticeTarget,
            Notice,
            AssessmentAssignment,
            Assessment,
            Result,
            StudentProgressSnapshot,
            Doubt,
            StudentProfile,
            TeacherProfile,
            User,
            Role,
            Batch,
            Standard,
            Branch,
            Subject,
            DailyThought,
        ]:
            await session.execute(delete(table))

        student_role = Role(code=RoleCode.STUDENT, name="Student")
        teacher_role = Role(code=RoleCode.TEACHER, name="Teacher")
        parent_role = Role(code=RoleCode.PARENT, name="Parent")
        admin_role = Role(code=RoleCode.ADMIN, name="Admin")
        session.add_all([student_role, teacher_role, parent_role, admin_role])
        await session.flush()

        branch = Branch(code="MAIN", name="Main Branch")
        session.add(branch)
        await session.flush()

        standard = Standard(branch_id=branch.id, name="Class 10")
        session.add(standard)
        await session.flush()

        batch = Batch(standard_id=standard.id, name="Batch A", academic_year=datetime.now(UTC).year)
        subject_math = Subject(code="MATH", name="Mathematics")
        subject_sci = Subject(code="SCI", name="Science")
        session.add_all([batch, subject_math, subject_sci])
        await session.flush()

        student_user = User(
            full_name="Demo Student",
            email="student@adr.local",
            phone="9999990001",
            password_hash=get_password_hash("Student@123"),
        )
        teacher_user = User(
            full_name="Demo Teacher",
            email="teacher@adr.local",
            phone="9999990002",
            password_hash=get_password_hash("Teacher@123"),
        )
        parent_user = User(
            full_name="Demo Parent",
            email="parent@adr.local",
            phone="9999990004",
            password_hash=get_password_hash("Parent@123"),
        )
        admin_user = User(
            full_name="Demo Admin",
            email="admin@adr.local",
            phone="9999990003",
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
            admission_no="ADM-1001",
            roll_no="10A-01",
            current_batch_id=batch.id,
        )
        teacher_profile = TeacherProfile(
            user_id=teacher_user.id,
            employee_code="EMP-1001",
            designation="Senior Faculty",
        )
        parent_profile = ParentProfile(user_id=parent_user.id)
        session.add_all([student_profile, teacher_profile, parent_profile])
        await session.flush()

        session.add_all(
            [
                TeacherBatchAssignment(
                    teacher_id=teacher_profile.id,
                    batch_id=batch.id,
                    subject_id=subject_math.id,
                ),
                ParentStudentLink(
                    parent_id=parent_profile.id,
                    student_id=student_profile.id,
                    relation_type="guardian",
                    is_primary=True,
                    is_active=True,
                ),
            ]
        )

        session.add(
            StudentBatchEnrollment(
                student_id=student_profile.id,
                batch_id=batch.id,
                from_date=date.today() - timedelta(days=90),
                to_date=None,
            )
        )

        notice = Notice(
            title="Welcome to ADR Platform",
            body="Your class schedule and notices are now available in app.",
            status=NoticeStatus.PUBLISHED,
            priority=10,
            publish_at=datetime.now(UTC) - timedelta(hours=1),
            created_by=admin_user.id,
        )
        session.add(notice)
        await session.flush()
        session.add_all(
            [
                NoticeTarget(notice_id=notice.id, target_type="all", target_id="all"),
                NoticeTarget(notice_id=notice.id, target_type="batch", target_id=batch.id),
                NoticeTarget(notice_id=notice.id, target_type="teacher", target_id=teacher_profile.id),
            ]
        )

        homework = Homework(
            title="Algebra worksheet",
            description="Solve questions 1-20 from chapter 4.",
            subject_id=subject_math.id,
            due_date=date.today() + timedelta(days=2),
            status=HomeworkStatus.PUBLISHED,
            created_by=teacher_user.id,
        )
        session.add(homework)
        await session.flush()
        session.add(HomeworkTarget(homework_id=homework.id, target_type="batch", target_id=batch.id))

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

        assessment = Assessment(
            title="Daily Practice Test - Algebra",
            description="20 questions",
            subject_id=subject_math.id,
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
            Result(
                assessment_id=assessment.id,
                student_id=student_profile.id,
                score=16,
                total_marks=20,
                rank=4,
                published_at=datetime.now(UTC) - timedelta(days=1),
            )
        )
        session.add(
            StudentProgressSnapshot(
                student_id=student_profile.id,
                period_type="monthly",
                period_start=date.today().replace(day=1),
                metrics={"average_score": 80, "attendance_pct": 92.5},
            )
        )

        session.add(
            Doubt(
                student_id=student_profile.id,
                subject_id=subject_math.id,
                topic="Linear Equations",
                description="Need help with elimination method.",
            )
        )

        invoice = FeeInvoice(
            student_id=student_profile.id,
            invoice_no="INV-1001",
            period_label="Apr-2026",
            due_date=date.today() + timedelta(days=10),
            amount=4500,
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
                external_ref="demo_pay_001",
                amount=2000,
                status="success",
                paid_at=datetime.now(UTC) - timedelta(days=5),
                metadata_json={"mode": "upi"},
            )
        )

        session.add(
            DailyThought(
                thought_date=date.today(),
                text="Consistency compounds into mastery.",
                is_active=True,
            )
        )

        session.add_all(
            [
                Notification(
                    recipient_user_id=student_user.id,
                    notification_type=NotificationType.SYSTEM,
                    title="Welcome",
                    body="Your dashboard is ready.",
                    is_read=False,
                ),
                Notification(
                    recipient_user_id=teacher_user.id,
                    notification_type=NotificationType.SYSTEM,
                    title="Welcome",
                    body="Your teacher dashboard is ready.",
                    is_read=False,
                ),
                Notification(
                    recipient_user_id=parent_user.id,
                    notification_type=NotificationType.SYSTEM,
                    title="Welcome",
                    body="Your parent dashboard is ready.",
                    is_read=False,
                ),
            ]
        )

        await session.commit()

        check_user = await session.execute(select(User).where(User.email == "student@adr.local"))
        assert check_user.scalar_one_or_none() is not None


if __name__ == "__main__":
    asyncio.run(seed())
