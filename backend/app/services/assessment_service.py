from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.db.models.academic import Subject
from app.db.models.assessment import Assessment, AssessmentAttempt, AssessmentQuestion, AttemptAnswer, QuestionBank
from app.db.models.enums import AttemptStatus
from app.db.models.results import Result
from app.repositories.assessment_repo import AssessmentRepository


class AssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssessmentRepository(session)

    @staticmethod
    def _enum_value(value) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _extract_class_level(class_name: str | None) -> int | None:
        text = (class_name or "").strip()
        if "10" in text:
            return 10
        if "11" in text:
            return 11
        if "12" in text:
            return 12
        return None

    @staticmethod
    def _normalize_stream(stream: str | None) -> str | None:
        value = (stream or "").strip().lower()
        if value in {"science", "sci"}:
            return "science"
        if value in {"commerce", "comm"}:
            return "commerce"
        if value:
            return "common"
        return None

    @staticmethod
    def _as_float(value: Decimal | float | int | None) -> float:
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    @staticmethod
    def _to_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _extract_selected_key(payload: dict | None) -> str | None:
        if not isinstance(payload, dict):
            return None

        candidates = [
            payload.get("selected_key"),
            payload.get("option_key"),
            payload.get("answer"),
            payload.get("selected_option"),
        ]

        for item in candidates:
            if isinstance(item, str) and item.strip():
                return item.strip().upper()

        index_value = payload.get("selected_index")
        if isinstance(index_value, int):
            # A,B,C... fallback when client sends index.
            return chr(ord("A") + index_value)

        return None

    @staticmethod
    def _extract_correct_key(question: QuestionBank) -> str | None:
        answer_key = question.answer_key if isinstance(question.answer_key, dict) else {}
        direct = answer_key.get("correct_option_key")
        if isinstance(direct, str) and direct.strip():
            return direct.strip().upper()

        options = question.options if isinstance(question.options, dict) else {}
        choices = options.get("choices") if isinstance(options.get("choices"), list) else []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            if bool(choice.get("is_correct")):
                key = choice.get("key")
                if isinstance(key, str) and key.strip():
                    return key.strip().upper()
        return None

    @staticmethod
    def _question_choices(question: QuestionBank) -> list[dict]:
        options = question.options if isinstance(question.options, dict) else {}
        choices = options.get("choices") if isinstance(options.get("choices"), list) else []
        normalized: list[dict] = []
        for idx, choice in enumerate(choices):
            if isinstance(choice, dict):
                key = choice.get("key")
                text = choice.get("text")
                if not isinstance(key, str) or not key.strip():
                    key = chr(ord("A") + idx)
                normalized.append({
                    "key": key.strip().upper(),
                    "text": str(text or "").strip(),
                })
            elif isinstance(choice, str):
                normalized.append({
                    "key": chr(ord("A") + idx),
                    "text": choice,
                })
        return normalized

    def _availability(
        self,
        *,
        assessment: Assessment,
        now: datetime,
        result: Result | None,
        latest_attempt: AssessmentAttempt | None,
    ) -> str:
        starts_at = self._to_utc(assessment.starts_at)
        ends_at = self._to_utc(assessment.ends_at)

        if result is not None:
            return "completed"

        if latest_attempt and latest_attempt.status in {AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED}:
            return "completed"

        if starts_at and now < starts_at:
            return "scheduled"

        if ends_at and now > ends_at:
            return "missed"

        return "live"

    async def _question_count_map(self, assessment_ids: list[str]) -> dict[str, int]:
        if not assessment_ids:
            return {}

        rows = (
            await self.session.execute(
                select(AssessmentQuestion.assessment_id, func.count().label("count"))
                .where(AssessmentQuestion.assessment_id.in_(assessment_ids))
                .group_by(AssessmentQuestion.assessment_id)
            )
        ).all()
        return {assessment_id: int(count) for assessment_id, count in rows}

    async def _result_map(self, assessment_ids: list[str], student_id: str) -> dict[str, Result]:
        if not assessment_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Result).where(Result.student_id == student_id, Result.assessment_id.in_(assessment_ids))
            )
        ).scalars().all()
        return {row.assessment_id: row for row in rows}

    async def _latest_attempt_map(self, assessment_ids: list[str], student_id: str) -> dict[str, AssessmentAttempt]:
        if not assessment_ids:
            return {}
        rows = (
            await self.session.execute(
                select(AssessmentAttempt)
                .where(
                    AssessmentAttempt.student_id == student_id,
                    AssessmentAttempt.assessment_id.in_(assessment_ids),
                )
                .order_by(AssessmentAttempt.assessment_id.asc(), AssessmentAttempt.attempt_no.desc())
            )
        ).scalars().all()

        latest: dict[str, AssessmentAttempt] = {}
        for row in rows:
            if row.assessment_id not in latest:
                latest[row.assessment_id] = row
        return latest

    async def _subject_map(self, subject_ids: set[str]) -> dict[str, Subject]:
        if not subject_ids:
            return {}
        rows = (
            await self.session.execute(select(Subject).where(Subject.id.in_(list(subject_ids))))
        ).scalars().all()
        return {row.id: row for row in rows}

    async def list_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
        assessment_type: str | None,
        status: str | None,
        subject_id: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        class_level = self._extract_class_level(class_name)
        normalized_stream = self._normalize_stream(stream)

        # Keep absent state in sync for missed windows.
        await self.materialize_absent_results_for_student(
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )

        rows, total = await self.repo.list_for_student(
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
            assessment_type=assessment_type,
            status=status,
            subject_id=subject_id,
            limit=limit,
            offset=offset,
        )

        assessment_ids = [row.id for row in rows]
        question_count_map = await self._question_count_map(assessment_ids)
        result_map = await self._result_map(assessment_ids, student_id)
        attempt_map = await self._latest_attempt_map(assessment_ids, student_id)
        subject_map = await self._subject_map({row.subject_id for row in rows})

        now = datetime.now(UTC)
        items: list[dict] = []
        for row in rows:
            result = result_map.get(row.id)
            latest_attempt = attempt_map.get(row.id)
            availability = self._availability(
                assessment=row,
                now=now,
                result=result,
                latest_attempt=latest_attempt,
            )

            score = self._as_float(result.score) if result else self._as_float(latest_attempt.score if latest_attempt else None)
            total_marks = self._as_float(row.total_marks)
            passing_marks = self._as_float(row.passing_marks)

            subject = subject_map.get(row.subject_id)
            items.append(
                {
                    "id": row.id,
                    "title": row.title,
                    "description": row.description,
                    "subject_id": row.subject_id,
                    "subject_name": subject.name if subject else None,
                    "topic": row.topic,
                    "class_level": row.class_level,
                    "stream": row.stream,
                    "assessment_type": self._enum_value(row.assessment_type),
                    "status": self._enum_value(row.status),
                    "availability": availability,
                    "starts_at": row.starts_at,
                    "ends_at": row.ends_at,
                    "duration_sec": int(row.duration_sec),
                    "duration_minutes": int(row.duration_sec) // 60,
                    "attempt_limit": int(row.attempt_limit),
                    "question_count": question_count_map.get(row.id, 0),
                    "total_marks": total_marks,
                    "passing_marks": passing_marks,
                    "has_submitted": availability == "completed",
                    "score": score if availability == "completed" else None,
                    "is_passed": (score >= passing_marks) if availability == "completed" else None,
                    "latest_attempt_id": latest_attempt.id if latest_attempt else None,
                }
            )

        return items, total

    async def get_test_detail(
        self,
        *,
        assessment_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        normalized_stream = self._normalize_stream(stream)

        assessment = await self.repo.get_assessment_for_student(
            assessment_id=assessment_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )
        if not assessment:
            raise NotFoundException("Assessment not found")

        questions = await self.repo.list_assessment_questions(assessment_id=assessment.id)
        subject = await self.session.get(Subject, assessment.subject_id)
        result = await self.repo.result_for_student(assessment_id=assessment.id, student_id=student_id)
        latest_attempt = await self.repo.latest_attempt_for_student(assessment_id=assessment.id, student_id=student_id)
        now = datetime.now(UTC)
        availability = self._availability(
            assessment=assessment,
            now=now,
            result=result,
            latest_attempt=latest_attempt,
        )

        return {
            "id": assessment.id,
            "title": assessment.title,
            "description": assessment.description,
            "subject_id": assessment.subject_id,
            "subject_name": subject.name if subject else None,
            "topic": assessment.topic,
            "class_level": assessment.class_level,
            "stream": assessment.stream,
            "assessment_type": self._enum_value(assessment.assessment_type),
            "status": self._enum_value(assessment.status),
            "availability": availability,
            "starts_at": assessment.starts_at,
            "ends_at": assessment.ends_at,
            "duration_sec": int(assessment.duration_sec),
            "duration_minutes": int(assessment.duration_sec) // 60,
            "attempt_limit": int(assessment.attempt_limit),
            "question_count": len(questions),
            "total_marks": self._as_float(assessment.total_marks),
            "passing_marks": self._as_float(assessment.passing_marks),
            "latest_attempt_id": latest_attempt.id if latest_attempt else None,
        }

    async def _serialize_attempt_questions(self, *, assessment_id: str) -> list[dict]:
        question_rows = await self.repo.list_assessment_questions(assessment_id=assessment_id)
        payload: list[dict] = []
        for aq, question in question_rows:
            payload.append(
                {
                    "seq_no": int(aq.seq_no),
                    "question_id": question.id,
                    "question_type": question.question_type,
                    "prompt": question.prompt,
                    "options": self._question_choices(question),
                    "marks": self._as_float(aq.marks),
                }
            )
        return payload

    async def start_attempt(
        self,
        *,
        assessment_id: str,
        student_id: str,
        batch_id: str | None,
        class_name: str | None,
        stream: str | None,
    ) -> dict:
        class_level = self._extract_class_level(class_name)
        normalized_stream = self._normalize_stream(stream)

        assessment = await self.repo.get_assessment_for_student(
            assessment_id=assessment_id,
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=normalized_stream,
        )
        if not assessment:
            raise NotFoundException("Assessment not found")

        existing_result = await self.repo.result_for_student(
            assessment_id=assessment.id,
            student_id=student_id,
        )
        if existing_result:
            raise ForbiddenException("Test already completed")

        now = datetime.now(UTC)
        starts_at = self._to_utc(assessment.starts_at)
        if starts_at and now < starts_at:
            raise ForbiddenException("Test is not live yet")

        ends_at = self._to_utc(assessment.ends_at)
        if ends_at and now > ends_at:
            # Immediate absent write for missed test.
            await self.repo.upsert_result(
                assessment_id=assessment.id,
                student_id=student_id,
                score=0,
                total_marks=self._as_float(assessment.total_marks),
                published_at=now,
            )
            await self.session.commit()
            raise ForbiddenException("Test window has ended")

        latest_attempt = await self.repo.latest_attempt_for_student(
            assessment_id=assessment.id,
            student_id=student_id,
        )
        if latest_attempt and latest_attempt.status == AttemptStatus.STARTED:
            latest_expires_at = self._to_utc(latest_attempt.expires_at)
            if latest_expires_at and now >= latest_expires_at:
                await self._finalize_attempt(latest_attempt, force_auto_submit=True)
                await self.session.commit()
                raise ForbiddenException("Test time exceeded and attempt auto-submitted")

            return {
                "attempt_id": latest_attempt.id,
                "status": self._enum_value(latest_attempt.status),
                "started_at": latest_attempt.started_at,
                "expires_at": latest_attempt.expires_at,
                "remaining_seconds": max(0, int(((latest_expires_at or now) - now).total_seconds())),
                "assessment": await self.get_test_detail(
                    assessment_id=assessment.id,
                    student_id=student_id,
                    batch_id=batch_id,
                    class_name=class_name,
                    stream=stream,
                ),
                "questions": await self._serialize_attempt_questions(assessment_id=assessment.id),
            }

        current_count = await self.repo.current_attempt_count(
            assessment_id=assessment.id,
            student_id=student_id,
        )
        if current_count >= int(assessment.attempt_limit):
            raise ForbiddenException("Attempt limit reached")

        attempt = await self.repo.create_attempt(
            assessment=assessment,
            student_id=student_id,
            attempt_no=current_count + 1,
        )
        await self.session.commit()

        return {
            "attempt_id": attempt.id,
            "status": self._enum_value(attempt.status),
            "started_at": attempt.started_at,
            "expires_at": attempt.expires_at,
            "remaining_seconds": max(0, int(((self._to_utc(attempt.expires_at) or datetime.now(UTC)) - datetime.now(UTC)).total_seconds())),
            "assessment": await self.get_test_detail(
                assessment_id=assessment.id,
                student_id=student_id,
                batch_id=batch_id,
                class_name=class_name,
                stream=stream,
            ),
            "questions": await self._serialize_attempt_questions(assessment_id=assessment.id),
        }

    async def save_answer(
        self,
        *,
        attempt_id: str,
        student_id: str,
        question_id: str,
        answer_payload: dict,
    ) -> dict:
        attempt = await self.repo.get_attempt(attempt_id=attempt_id, student_id=student_id)
        if not attempt:
            raise NotFoundException("Attempt not found")

        if attempt.status != AttemptStatus.STARTED:
            raise ForbiddenException("Attempt already submitted")

        now = datetime.now(UTC)
        attempt_expires_at = self._to_utc(attempt.expires_at)
        if attempt_expires_at and now >= attempt_expires_at:
            await self._finalize_attempt(attempt, force_auto_submit=True)
            await self.session.commit()
            raise ForbiddenException("Time exceeded. Attempt auto-submitted")

        exists = await self.repo.question_exists_in_assessment(
            assessment_id=attempt.assessment_id,
            question_id=question_id,
        )
        if not exists:
            raise NotFoundException("Question not found in this assessment")

        selected_key = self._extract_selected_key(answer_payload)
        if selected_key is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="selected option key is required",
            )

        normalized_payload = {
            "selected_key": selected_key,
        }
        await self.repo.upsert_answer(
            attempt_id=attempt_id,
            question_id=question_id,
            answer_payload=normalized_payload,
        )
        await self.session.commit()
        return {
            "attempt_id": attempt_id,
            "question_id": question_id,
            "saved": True,
            "selected_key": selected_key,
        }

    async def _finalize_attempt(self, attempt: AssessmentAttempt, *, force_auto_submit: bool) -> dict:
        assessment = await self.session.get(Assessment, attempt.assessment_id)
        if not assessment:
            raise NotFoundException("Assessment not found")

        if attempt.status in {AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED}:
            result = await self.repo.result_for_student(
                assessment_id=attempt.assessment_id,
                student_id=attempt.student_id,
            )
            score = self._as_float(result.score if result else attempt.score)
            total_marks = self._as_float(assessment.total_marks)
            passing_marks = self._as_float(assessment.passing_marks)
            return {
                "attempt_id": attempt.id,
                "status": self._enum_value(attempt.status),
                "score": score,
                "total_marks": total_marks,
                "passing_marks": passing_marks,
                "is_passed": score >= passing_marks,
                "submitted_at": attempt.submitted_at,
                "auto_submitted": attempt.status == AttemptStatus.AUTO_SUBMITTED,
                "question_evaluation": [],
            }

        question_rows = await self.repo.list_assessment_questions(assessment_id=assessment.id)
        answer_rows = await self.repo.get_answer_rows_for_attempt(attempt_id=attempt.id)
        answer_map: dict[str, AttemptAnswer] = {row.question_id: row for row in answer_rows}

        total_score = 0.0
        question_eval: list[dict] = []

        for aq, question in question_rows:
            answer_row = answer_map.get(question.id)
            selected_key = self._extract_selected_key(answer_row.answer_payload if answer_row else None)
            correct_key = self._extract_correct_key(question)

            is_correct = bool(selected_key and correct_key and selected_key == correct_key)
            marks_awarded = 0.0
            if is_correct:
                marks_awarded = self._as_float(aq.marks)
            elif selected_key and bool(assessment.negative_marking_enabled):
                marks_awarded = -self._as_float(aq.negative_marks)

            if answer_row is not None:
                answer_row.is_correct = is_correct
                answer_row.marks_obtained = marks_awarded

            total_score += marks_awarded
            question_eval.append(
                {
                    "seq_no": int(aq.seq_no),
                    "question_id": question.id,
                    "prompt": question.prompt,
                    "selected_key": selected_key,
                    "correct_key": correct_key,
                    "is_correct": is_correct,
                    "marks_awarded": marks_awarded,
                    "max_marks": self._as_float(aq.marks),
                }
            )

        now = datetime.now(UTC)
        attempt_expires_at = self._to_utc(attempt.expires_at)
        if force_auto_submit or (attempt_expires_at and now >= attempt_expires_at):
            attempt.status = AttemptStatus.AUTO_SUBMITTED
        else:
            attempt.status = AttemptStatus.SUBMITTED
        attempt.submitted_at = now
        attempt.score = total_score

        total_marks = self._as_float(assessment.total_marks)
        if total_marks <= 0:
            total_marks = sum(self._as_float(aq.marks) for aq, _question in question_rows)
            assessment.total_marks = total_marks

        await self.repo.upsert_result(
            assessment_id=assessment.id,
            student_id=attempt.student_id,
            score=total_score,
            total_marks=total_marks,
            published_at=now,
        )

        passing_marks = self._as_float(assessment.passing_marks)
        return {
            "attempt_id": attempt.id,
            "status": self._enum_value(attempt.status),
            "score": total_score,
            "total_marks": total_marks,
            "passing_marks": passing_marks,
            "is_passed": total_score >= passing_marks,
            "submitted_at": attempt.submitted_at,
            "auto_submitted": attempt.status == AttemptStatus.AUTO_SUBMITTED,
            "question_evaluation": question_eval,
        }

    async def submit_attempt(self, *, attempt_id: str, student_id: str) -> dict:
        attempt = await self.repo.get_attempt(attempt_id=attempt_id, student_id=student_id)
        if not attempt:
            raise NotFoundException("Attempt not found")

        summary = await self._finalize_attempt(
            attempt,
            force_auto_submit=(lambda ex: (datetime.now(UTC) >= ex) if ex else False)(self._to_utc(attempt.expires_at)),
        )
        await self.session.commit()
        return summary

    async def get_attempt_detail(self, *, attempt_id: str, student_id: str) -> dict:
        attempt = await self.repo.get_attempt(attempt_id=attempt_id, student_id=student_id)
        if not attempt:
            raise NotFoundException("Attempt not found")

        normalized_expires = self._to_utc(attempt.expires_at)
        if attempt.status == AttemptStatus.STARTED and normalized_expires and datetime.now(UTC) >= normalized_expires:
            await self._finalize_attempt(attempt, force_auto_submit=True)
            await self.session.commit()

        assessment = await self.session.get(Assessment, attempt.assessment_id)
        if not assessment:
            raise NotFoundException("Assessment not found")

        question_rows = await self.repo.list_assessment_questions(assessment_id=assessment.id)
        answer_rows = await self.repo.get_answer_rows_for_attempt(attempt_id=attempt.id)
        answer_map: dict[str, AttemptAnswer] = {row.question_id: row for row in answer_rows}

        is_completed = attempt.status in {AttemptStatus.SUBMITTED, AttemptStatus.AUTO_SUBMITTED}
        questions: list[dict] = []
        for aq, question in question_rows:
            answer_row = answer_map.get(question.id)
            selected_key = self._extract_selected_key(answer_row.answer_payload if answer_row else None)
            correct_key = self._extract_correct_key(question) if is_completed else None
            is_correct = bool(answer_row.is_correct) if is_completed and answer_row is not None else None
            marks_awarded = self._as_float(answer_row.marks_obtained) if is_completed and answer_row else None
            questions.append(
                {
                    "seq_no": int(aq.seq_no),
                    "question_id": question.id,
                    "prompt": question.prompt,
                    "options": self._question_choices(question),
                    "max_marks": self._as_float(aq.marks),
                    "selected_key": selected_key,
                    "correct_key": correct_key,
                    "is_correct": is_correct,
                    "marks_awarded": marks_awarded,
                }
            )

        result = await self.repo.result_for_student(
            assessment_id=assessment.id,
            student_id=student_id,
        )

        now = datetime.now(UTC)
        remaining_seconds = 0
        if attempt.status == AttemptStatus.STARTED:
            remaining_seconds = max(0, int(((normalized_expires or now) - now).total_seconds()))

        score = self._as_float(result.score if result else attempt.score)
        total_marks = self._as_float(assessment.total_marks)
        passing_marks = self._as_float(assessment.passing_marks)

        return {
            "attempt_id": attempt.id,
            "assessment_id": assessment.id,
            "status": self._enum_value(attempt.status),
            "started_at": attempt.started_at,
            "expires_at": attempt.expires_at,
            "submitted_at": attempt.submitted_at,
            "remaining_seconds": remaining_seconds,
            "score": score if is_completed else None,
            "total_marks": total_marks,
            "passing_marks": passing_marks,
            "is_passed": (score >= passing_marks) if is_completed else None,
            "auto_submitted": attempt.status == AttemptStatus.AUTO_SUBMITTED,
            "questions": questions,
        }

    async def materialize_absent_results_for_student(
        self,
        *,
        student_id: str,
        batch_id: str | None,
        class_level: int | None,
        stream: str | None,
    ) -> int:
        rows, _ = await self.repo.list_for_student(
            student_id=student_id,
            batch_id=batch_id,
            class_level=class_level,
            stream=stream,
            assessment_type=None,
            status=None,
            subject_id=None,
            limit=200,
            offset=0,
        )

        now = datetime.now(UTC)
        changed = 0

        for assessment in rows:
            assessment_ends_at = self._to_utc(assessment.ends_at)
            if not assessment_ends_at or assessment_ends_at > now:
                continue

            result = await self.repo.result_for_student(
                assessment_id=assessment.id,
                student_id=student_id,
            )
            if result is not None:
                continue

            latest_attempt = await self.repo.latest_attempt_for_student(
                assessment_id=assessment.id,
                student_id=student_id,
            )

            if latest_attempt and latest_attempt.status == AttemptStatus.STARTED:
                await self._finalize_attempt(latest_attempt, force_auto_submit=True)
                changed += 1
                continue

            await self.repo.upsert_result(
                assessment_id=assessment.id,
                student_id=student_id,
                score=0,
                total_marks=self._as_float(assessment.total_marks),
                published_at=now,
            )
            changed += 1

        if changed:
            await self.session.commit()
        return changed

    async def process_scheduled_events(self, *, attempt_limit: int = 500, assessment_limit: int = 200) -> dict:
        auto_submitted = 0
        absent_marked = 0

        expired_attempts = await self.repo.list_expired_started_attempts(limit=attempt_limit)
        for attempt in expired_attempts:
            await self._finalize_attempt(attempt, force_auto_submit=True)
            auto_submitted += 1

        ended_assessments = await self.repo.list_ended_assessments_for_absent(limit=assessment_limit)
        now = datetime.now(UTC)

        for assessment in ended_assessments:
            student_ids = await self.repo.list_assigned_students_for_assessment(assessment_id=assessment.id)
            for student_id in student_ids:
                existing = await self.repo.result_for_student(
                    assessment_id=assessment.id,
                    student_id=student_id,
                )
                if existing is not None:
                    continue

                latest_attempt = await self.repo.latest_attempt_for_student(
                    assessment_id=assessment.id,
                    student_id=student_id,
                )
                if latest_attempt and latest_attempt.status == AttemptStatus.STARTED:
                    await self._finalize_attempt(latest_attempt, force_auto_submit=True)
                    auto_submitted += 1
                else:
                    await self.repo.upsert_result(
                        assessment_id=assessment.id,
                        student_id=student_id,
                        score=0,
                        total_marks=self._as_float(assessment.total_marks),
                        published_at=now,
                    )
                    absent_marked += 1

            await self.repo.mark_assessment_completed(assessment_id=assessment.id)

        await self.session.commit()
        return {
            "expired_attempts_processed": auto_submitted,
            "absent_results_created": absent_marked,
            "ended_assessments_scanned": len(ended_assessments),
        }
