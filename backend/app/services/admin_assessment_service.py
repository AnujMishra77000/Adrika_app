from __future__ import annotations

import json
from datetime import UTC, datetime

from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.keys import student_dashboard_key, student_unread_notifications_key
from app.cache.utils import delete_keys
from app.core.exceptions import NotFoundException
from app.db.models.academic import Batch, Standard, StudentProfile, Subject, SubjectAcademicScope
from app.db.models.assessment import Assessment, AssessmentAssignment, AssessmentQuestion, QuestionBank
from app.db.models.audit import AuditLog
from app.db.models.enums import AssessmentStatus, AssessmentType, NotificationType, UserStatus
from app.db.models.notification import Notification
from app.db.models.user import User
from app.schemas.admin import (
    AdminAssessmentAssignDTO,
    AdminAssessmentBuildDTO,
    AdminQuestionBankCreateDTO,
    AdminQuestionBankUpdateDTO,
)


class AdminAssessmentService:
    def __init__(self, session: AsyncSession, cache: Redis | None = None) -> None:
        self.session = session
        self.cache = cache

    async def _audit(
        self,
        *,
        actor_user_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        before_state: dict | None,
        after_state: dict | None,
        ip_address: str | None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_user_id=actor_user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                before_state=json.dumps(before_state, default=str) if before_state is not None else None,
                after_state=json.dumps(after_state, default=str) if after_state is not None else None,
                ip_address=ip_address,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _normalize_stream(stream: str | None) -> str:
        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        return "common"

    @staticmethod
    def _extract_grade(class_name: str | None, standard_name: str | None) -> int | None:
        source = f"{class_name or ''} {standard_name or ''}".lower()
        if "10" in source:
            return 10
        if "11" in source:
            return 11
        if "12" in source:
            return 12
        return None

    @staticmethod
    def _validate_class_stream(class_level: int, stream: str | None) -> str | None:
        normalized = None if stream is None else AdminAssessmentService._normalize_stream(stream)
        if class_level == 10 and normalized is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stream is not allowed for class 10",
            )
        if class_level in {11, 12} and normalized not in {"science", "commerce"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stream is required for class 11 and 12",
            )
        return normalized

    async def _ensure_subject_scope(
        self,
        *,
        subject_id: str,
        class_level: int,
        stream: str | None,
    ) -> None:
        # Backward compatibility: if a subject has no explicit scope rows, treat it as legacy-global.
        total_scope_rows = (
            await self.session.execute(
                select(func.count()).select_from(SubjectAcademicScope).where(
                    SubjectAcademicScope.subject_id == subject_id
                )
            )
        ).scalar_one()

        if int(total_scope_rows or 0) == 0:
            return

        scope_stream = "common" if class_level == 10 else self._normalize_stream(stream)
        mapped = (
            await self.session.execute(
                select(func.count()).select_from(SubjectAcademicScope).where(
                    SubjectAcademicScope.subject_id == subject_id,
                    SubjectAcademicScope.class_level == class_level,
                    SubjectAcademicScope.stream == scope_stream,
                )
            )
        ).scalar_one()

        if int(mapped or 0) == 0:
            if class_level == 10:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Selected subject is not mapped for class 10",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Selected subject is not mapped for selected class/stream",
            )

    async def _resolve_target_students_and_users(self, targets: list[dict]) -> tuple[list[str], list[str]]:
        rows = (
            await self.session.execute(
                select(StudentProfile, User, Batch, Standard)
                .join(User, User.id == StudentProfile.user_id)
                .outerjoin(Batch, Batch.id == StudentProfile.current_batch_id)
                .outerjoin(Standard, Standard.id == Batch.standard_id)
                .where(User.status == UserStatus.ACTIVE)
            )
        ).all()

        student_ids: set[str] = set()
        user_ids: set[str] = set()

        for target in targets:
            target_type = target.get("target_type")
            target_id = target.get("target_id")
            if not isinstance(target_type, str) or not isinstance(target_id, str):
                continue

            if target_type in {"all", "all_students"} and target_id == "all":
                for profile, user, _batch, _standard in rows:
                    student_ids.add(profile.id)
                    user_ids.add(user.id)
                continue

            if target_type == "student":
                for profile, user, _batch, _standard in rows:
                    if profile.id == target_id:
                        student_ids.add(profile.id)
                        user_ids.add(user.id)
                continue

            if target_type == "batch":
                for profile, user, _batch, _standard in rows:
                    if profile.current_batch_id == target_id:
                        student_ids.add(profile.id)
                        user_ids.add(user.id)
                continue

            if target_type == "grade":
                grade_raw, _, stream_raw = target_id.partition(":")
                try:
                    grade = int(grade_raw)
                except ValueError:
                    continue
                stream_filter = self._normalize_stream(stream_raw) if stream_raw else None

                for profile, user, _batch, standard in rows:
                    student_grade = self._extract_grade(profile.class_name, standard.name if standard else None)
                    if student_grade != grade:
                        continue

                    if stream_filter and grade in {11, 12}:
                        student_stream = self._normalize_stream(profile.stream)
                        if student_stream != stream_filter:
                            continue

                    student_ids.add(profile.id)
                    user_ids.add(user.id)

        return sorted(student_ids), sorted(user_ids)

    async def list_saved_questions(
        self,
        *,
        class_level: int | None,
        stream: str | None,
        subject_id: str | None,
        topic: str | None,
        search: str | None,
        is_active: bool | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        query = select(QuestionBank, Subject).join(Subject, Subject.id == QuestionBank.subject_id)

        if class_level is not None:
            query = query.where(QuestionBank.class_level == class_level)
        if stream:
            query = query.where(QuestionBank.stream == self._normalize_stream(stream))
        if subject_id:
            query = query.where(QuestionBank.subject_id == subject_id)
        if topic:
            query = query.where(QuestionBank.topic.ilike(f"%{topic}%"))
        if search:
            query = query.where(QuestionBank.prompt.ilike(f"%{search}%"))
        if is_active is not None:
            query = query.where(QuestionBank.is_active.is_(is_active))

        total = (await self.session.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
        rows = (
            await self.session.execute(
                query.order_by(QuestionBank.updated_at.desc()).limit(limit).offset(offset)
            )
        ).all()

        items: list[dict] = []
        for question, subject in rows:
            options = question.options if isinstance(question.options, dict) else {}
            choices = options.get("choices") if isinstance(options.get("choices"), list) else []
            answer_key = question.answer_key if isinstance(question.answer_key, dict) else {}

            items.append(
                {
                    "id": question.id,
                    "class_level": question.class_level,
                    "stream": question.stream,
                    "subject": {
                        "id": subject.id,
                        "code": subject.code,
                        "name": subject.name,
                    },
                    "topic": question.topic,
                    "question_type": question.question_type,
                    "prompt": question.prompt,
                    "options": choices,
                    "correct_option_key": answer_key.get("correct_option_key"),
                    "difficulty": question.difficulty,
                    "default_marks": float(question.default_marks),
                    "is_active": bool(question.is_active),
                    "created_at": question.created_at,
                    "updated_at": question.updated_at,
                }
            )

        return items, total

    async def create_saved_question(
        self,
        *,
        payload: AdminQuestionBankCreateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        stream = self._validate_class_stream(payload.class_level, payload.stream)

        subject = await self.session.get(Subject, payload.subject_id)
        if not subject:
            raise NotFoundException("Subject not found")

        await self._ensure_subject_scope(
            subject_id=payload.subject_id,
            class_level=payload.class_level,
            stream=stream,
        )

        choices = [
            {
                "key": item.key.strip().upper(),
                "text": item.text.strip(),
            }
            for item in payload.options
        ]

        record = QuestionBank(
            class_level=payload.class_level,
            stream=stream,
            subject_id=payload.subject_id,
            topic=payload.topic.strip(),
            question_type="mcq_single",
            prompt=payload.prompt.strip(),
            options={"choices": choices},
            answer_key={"correct_option_key": payload.correct_option_key.strip().upper()},
            difficulty=payload.difficulty,
            default_marks=payload.default_marks,
            is_active=payload.is_active,
        )
        self.session.add(record)
        await self.session.flush()

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.assessment.question_bank.create",
            entity_type="question_bank",
            entity_id=record.id,
            before_state=None,
            after_state={
                "class_level": record.class_level,
                "stream": record.stream,
                "subject_id": record.subject_id,
                "topic": record.topic,
                "is_active": record.is_active,
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        return {
            "id": record.id,
            "class_level": record.class_level,
            "stream": record.stream,
            "subject_id": record.subject_id,
            "subject_name": subject.name,
            "topic": record.topic,
            "prompt": record.prompt,
            "options": choices,
            "correct_option_key": payload.correct_option_key.strip().upper(),
            "default_marks": float(record.default_marks),
            "is_active": bool(record.is_active),
        }

    async def update_saved_question(
        self,
        *,
        question_id: str,
        payload: AdminQuestionBankUpdateDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        record = await self.session.get(QuestionBank, question_id)
        if not record:
            raise NotFoundException("Question not found")

        before = {
            "class_level": record.class_level,
            "stream": record.stream,
            "topic": record.topic,
            "prompt": record.prompt,
            "difficulty": record.difficulty,
            "default_marks": float(record.default_marks),
            "is_active": bool(record.is_active),
        }

        if payload.class_level is not None:
            record.class_level = payload.class_level
        if payload.stream is not None or payload.class_level is not None:
            target_class = record.class_level or payload.class_level
            if target_class is None:
                raise HTTPException(status_code=400, detail="class_level is required")
            record.stream = self._validate_class_stream(target_class, payload.stream)
        if payload.subject_id is not None:
            subject = await self.session.get(Subject, payload.subject_id)
            if not subject:
                raise NotFoundException("Subject not found")
            record.subject_id = payload.subject_id

        await self._ensure_subject_scope(
            subject_id=record.subject_id,
            class_level=record.class_level,
            stream=record.stream,
        )
        if payload.topic is not None:
            record.topic = payload.topic.strip()
        if payload.prompt is not None:
            record.prompt = payload.prompt.strip()
        if payload.options is not None:
            choices = [{"key": item.key.strip().upper(), "text": item.text.strip()} for item in payload.options]
            record.options = {"choices": choices}
            if payload.correct_option_key is None:
                raise HTTPException(status_code=400, detail="correct_option_key is required when options are updated")
        if payload.correct_option_key is not None:
            record.answer_key = {"correct_option_key": payload.correct_option_key.strip().upper()}
        if payload.difficulty is not None:
            record.difficulty = payload.difficulty
        if payload.default_marks is not None:
            record.default_marks = payload.default_marks
        if payload.is_active is not None:
            record.is_active = payload.is_active

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.assessment.question_bank.update",
            entity_type="question_bank",
            entity_id=record.id,
            before_state=before,
            after_state={
                "class_level": record.class_level,
                "stream": record.stream,
                "topic": record.topic,
                "prompt": record.prompt,
                "difficulty": record.difficulty,
                "default_marks": float(record.default_marks),
                "is_active": bool(record.is_active),
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        return {
            "id": record.id,
            "class_level": record.class_level,
            "stream": record.stream,
            "subject_id": record.subject_id,
            "topic": record.topic,
            "prompt": record.prompt,
            "difficulty": record.difficulty,
            "default_marks": float(record.default_marks),
            "is_active": bool(record.is_active),
        }

    async def delete_saved_question(
        self,
        *,
        question_id: str,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        record = await self.session.get(QuestionBank, question_id)
        if not record:
            raise NotFoundException("Question not found")

        linked_count = (
            await self.session.execute(
                select(func.count()).select_from(AssessmentQuestion).where(
                    AssessmentQuestion.question_id == question_id
                )
            )
        ).scalar_one()

        if int(linked_count or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Question is already used in one or more tests. Deactivate it instead of deleting.",
            )

        before = {
            "id": record.id,
            "class_level": record.class_level,
            "stream": record.stream,
            "subject_id": record.subject_id,
            "topic": record.topic,
            "prompt": record.prompt,
            "difficulty": record.difficulty,
            "default_marks": float(record.default_marks),
            "is_active": bool(record.is_active),
        }

        await self.session.execute(delete(QuestionBank).where(QuestionBank.id == question_id))

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.assessment.question_bank.delete",
            entity_type="question_bank",
            entity_id=question_id,
            before_state=before,
            after_state={"deleted": True},
            ip_address=ip_address,
        )

        await self.session.commit()
        return {"id": question_id, "deleted": True}

    async def create_test(
        self,
        *,
        payload: AdminAssessmentBuildDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        stream = self._validate_class_stream(payload.class_level, payload.stream)

        subject = await self.session.get(Subject, payload.subject_id)
        if not subject:
            raise NotFoundException("Subject not found")

        await self._ensure_subject_scope(
            subject_id=payload.subject_id,
            class_level=payload.class_level,
            stream=stream,
        )

        question_ids = [item.question_id for item in payload.questions]
        question_rows = (
            await self.session.execute(
                select(QuestionBank).where(
                    QuestionBank.id.in_(question_ids),
                    QuestionBank.is_active.is_(True),
                )
            )
        ).scalars().all()
        question_map = {row.id: row for row in question_rows}

        missing = [question_id for question_id in question_ids if question_id not in question_map]
        if missing:
            raise HTTPException(status_code=400, detail=f"Question(s) not found or inactive: {', '.join(missing[:5])}")

        total_marks = 0.0
        for selection in payload.questions:
            question = question_map[selection.question_id]
            if question.subject_id != payload.subject_id:
                raise HTTPException(status_code=400, detail="All selected questions must belong to the selected subject")
            if question.class_level is not None and question.class_level != payload.class_level:
                raise HTTPException(status_code=400, detail="Question class level mismatch")
            if payload.class_level in {11, 12} and question.stream is not None:
                if self._normalize_stream(question.stream) != stream:
                    raise HTTPException(status_code=400, detail="Question stream mismatch")
            total_marks += float(selection.marks)

        if payload.passing_marks > total_marks:
            raise HTTPException(status_code=400, detail="passing_marks cannot exceed total_marks")

        assessment = Assessment(
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            subject_id=payload.subject_id,
            class_level=payload.class_level,
            stream=stream,
            topic=payload.topic.strip() if payload.topic else None,
            assessment_type=AssessmentType(payload.assessment_type),
            status=AssessmentStatus.DRAFT,
            starts_at=None,
            ends_at=None,
            duration_sec=payload.duration_minutes * 60,
            attempt_limit=payload.attempt_limit,
            total_marks=total_marks,
            passing_marks=payload.passing_marks,
            negative_marking_enabled=False,
        )
        self.session.add(assessment)
        await self.session.flush()

        for seq, selection in enumerate(payload.questions, start=1):
            self.session.add(
                AssessmentQuestion(
                    assessment_id=assessment.id,
                    question_id=selection.question_id,
                    seq_no=seq,
                    marks=selection.marks,
                    negative_marks=selection.negative_marks,
                )
            )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.assessment.create_test",
            entity_type="assessment",
            entity_id=assessment.id,
            before_state=None,
            after_state={
                "title": assessment.title,
                "subject_id": assessment.subject_id,
                "class_level": assessment.class_level,
                "stream": assessment.stream,
                "question_count": len(payload.questions),
                "total_marks": total_marks,
                "passing_marks": payload.passing_marks,
                "status": assessment.status.value,
            },
            ip_address=ip_address,
        )

        await self.session.commit()
        return {
            "id": assessment.id,
            "title": assessment.title,
            "status": assessment.status.value,
            "class_level": assessment.class_level,
            "stream": assessment.stream,
            "subject": {
                "id": subject.id,
                "code": subject.code,
                "name": subject.name,
            },
            "question_count": len(payload.questions),
            "duration_minutes": payload.duration_minutes,
            "total_marks": total_marks,
            "passing_marks": payload.passing_marks,
        }

    async def assign_test(
        self,
        *,
        assessment_id: str,
        payload: AdminAssessmentAssignDTO,
        actor_user_id: str,
        ip_address: str | None,
    ) -> dict:
        assessment = await self.session.get(Assessment, assessment_id)
        if not assessment:
            raise NotFoundException("Assessment not found")

        if payload.ends_at <= payload.starts_at:
            raise HTTPException(status_code=400, detail="ends_at must be after starts_at")

        if payload.targets:
            targets = [target.model_dump() for target in payload.targets]
        else:
            if assessment.class_level is None:
                raise HTTPException(status_code=400, detail="targets are required when assessment class is not set")
            if assessment.class_level in {11, 12}:
                stream = self._normalize_stream(assessment.stream)
                targets = [{"target_type": "grade", "target_id": f"{assessment.class_level}:{stream}"}]
            else:
                targets = [{"target_type": "grade", "target_id": str(assessment.class_level)}]

        before = {
            "status": assessment.status.value,
            "starts_at": assessment.starts_at,
            "ends_at": assessment.ends_at,
        }

        assessment.starts_at = payload.starts_at
        assessment.ends_at = payload.ends_at
        if payload.publish:
            assessment.status = AssessmentStatus.PUBLISHED

        await self.session.execute(
            delete(AssessmentAssignment).where(AssessmentAssignment.assessment_id == assessment.id)
        )
        for target in targets:
            self.session.add(
                AssessmentAssignment(
                    assessment_id=assessment.id,
                    target_type=target["target_type"],
                    target_id=target["target_id"],
                )
            )

        student_ids, user_ids = await self._resolve_target_students_and_users(targets)

        if payload.publish and payload.send_notification:
            title = f"New Test Assigned: {assessment.title}"
            starts_label = payload.starts_at.astimezone(UTC).strftime("%d %b %Y %H:%M UTC")
            body = f"{assessment.title} is scheduled. Start window opens at {starts_label}."
            for user_id in user_ids:
                self.session.add(
                    Notification(
                        recipient_user_id=user_id,
                        notification_type=NotificationType.TEST,
                        title=title,
                        body=body,
                        metadata_json={
                            "source": "test",
                            "assessment_id": assessment.id,
                            "class_level": assessment.class_level,
                            "stream": assessment.stream,
                            "starts_at": payload.starts_at.isoformat(),
                            "ends_at": payload.ends_at.isoformat(),
                        },
                        is_read=False,
                    )
                )

        await self._audit(
            actor_user_id=actor_user_id,
            action="admin.assessment.assign",
            entity_type="assessment",
            entity_id=assessment.id,
            before_state=before,
            after_state={
                "status": assessment.status.value,
                "starts_at": assessment.starts_at,
                "ends_at": assessment.ends_at,
                "targets": targets,
                "assigned_students": len(student_ids),
            },
            ip_address=ip_address,
        )

        await self.session.commit()

        if self.cache is not None:
            cache_keys = [student_dashboard_key(student_id) for student_id in student_ids]
            cache_keys.extend(student_unread_notifications_key(user_id) for user_id in user_ids)
            await delete_keys(self.cache, cache_keys)

        return {
            "id": assessment.id,
            "title": assessment.title,
            "status": assessment.status.value,
            "starts_at": assessment.starts_at,
            "ends_at": assessment.ends_at,
            "target_count": len(targets),
            "assigned_students": len(student_ids),
            "notifications_created": len(user_ids) if payload.publish and payload.send_notification else 0,
        }

    async def list_test_questions(self, *, assessment_id: str) -> dict:
        assessment = await self.session.get(Assessment, assessment_id)
        if not assessment:
            raise NotFoundException("Assessment not found")

        rows = (
            await self.session.execute(
                select(AssessmentQuestion, QuestionBank)
                .join(QuestionBank, QuestionBank.id == AssessmentQuestion.question_id)
                .where(AssessmentQuestion.assessment_id == assessment.id)
                .order_by(AssessmentQuestion.seq_no.asc())
            )
        ).all()

        items: list[dict] = []
        for link, question in rows:
            options = question.options if isinstance(question.options, dict) else {}
            choices = options.get("choices") if isinstance(options.get("choices"), list) else []
            answer_key = question.answer_key if isinstance(question.answer_key, dict) else {}
            items.append(
                {
                    "seq_no": int(link.seq_no),
                    "question_id": question.id,
                    "prompt": question.prompt,
                    "topic": question.topic,
                    "options": choices,
                    "correct_option_key": answer_key.get("correct_option_key"),
                    "marks": float(link.marks),
                    "negative_marks": float(link.negative_marks),
                }
            )

        return {
            "assessment": {
                "id": assessment.id,
                "title": assessment.title,
                "status": assessment.status.value,
                "class_level": assessment.class_level,
                "stream": assessment.stream,
                "subject_id": assessment.subject_id,
                "topic": assessment.topic,
                "total_marks": float(assessment.total_marks),
                "passing_marks": float(assessment.passing_marks),
            },
            "items": items,
        }
