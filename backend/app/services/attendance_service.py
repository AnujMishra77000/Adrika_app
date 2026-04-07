from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.attendance_repo import AttendanceRepository


class AttendanceService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AttendanceRepository(session)

    async def list_for_student(
        self,
        *,
        student_id: str,
        date_from: date | None,
        date_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        rows, total = await self.repo.list_for_student(
            student_id=student_id,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            offset=offset,
        )
        return [
            {
                "id": row.id,
                "attendance_date": row.attendance_date,
                "session_code": row.session_code,
                "status": row.status.value if hasattr(row.status, "value") else str(row.status),
                "source": row.source,
            }
            for row in rows
        ], total

    async def summary_for_student(self, *, student_id: str, date_from: date | None, date_to: date | None) -> dict:
        return await self.repo.summary_for_student(student_id=student_id, date_from=date_from, date_to=date_to)
