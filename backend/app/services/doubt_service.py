from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.repositories.doubt_repo import DoubtRepository


class DoubtService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DoubtRepository(session)

    async def list_for_student(
        self,
        *,
        student_id: str,
        status: str | None,
        subject_id: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        rows, total = await self.repo.list_for_student(
            student_id=student_id,
            status=status,
            subject_id=subject_id,
            query=query,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": row.id,
                "subject_id": row.subject_id,
                "topic": row.topic,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "priority": row.priority,
                "created_at": row.created_at,
            }
            for row in rows
        ], total

    async def create(self, *, student_id: str, subject_id: str, topic: str, description: str) -> dict:
        doubt = await self.repo.create_doubt(
            student_id=student_id,
            subject_id=subject_id,
            topic=topic,
            description=description,
        )
        await self.session.commit()
        return {
            "id": doubt.id,
            "subject_id": doubt.subject_id,
            "topic": doubt.topic,
            "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
            "priority": doubt.priority,
            "created_at": doubt.created_at,
        }

    async def get_detail(self, *, student_id: str, doubt_id: str) -> dict:
        doubt = await self.repo.get_doubt_for_student(doubt_id=doubt_id, student_id=student_id)
        if not doubt:
            raise NotFoundException("Doubt not found")

        messages = await self.repo.list_messages(doubt_id=doubt.id)
        return {
            "doubt": {
                "id": doubt.id,
                "subject_id": doubt.subject_id,
                "topic": doubt.topic,
                "description": doubt.description,
                "status": doubt.status.value if hasattr(doubt.status, "value") else str(doubt.status),
                "priority": doubt.priority,
                "created_at": doubt.created_at,
            },
            "messages": [
                {
                    "id": message.id,
                    "sender_user_id": message.sender_user_id,
                    "message": message.message,
                    "created_at": message.created_at,
                }
                for message in messages
            ],
        }

    async def add_message(self, *, student_id: str, user_id: str, doubt_id: str, message: str) -> dict:
        doubt = await self.repo.get_doubt_for_student(doubt_id=doubt_id, student_id=student_id)
        if not doubt:
            raise NotFoundException("Doubt not found")

        saved = await self.repo.add_message(doubt_id=doubt_id, sender_user_id=user_id, message=message)
        await self.session.commit()
        return {
            "id": saved.id,
            "sender_user_id": saved.sender_user_id,
            "message": saved.message,
            "created_at": saved.created_at,
        }
