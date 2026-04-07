from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attendance import AttendanceRecord
from app.db.models.enums import AttendanceStatus


class AttendanceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_student(
        self,
        *,
        student_id: str,
        date_from: date | None,
        date_to: date | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AttendanceRecord], int]:
        filters = [AttendanceRecord.student_id == student_id]
        if date_from:
            filters.append(AttendanceRecord.attendance_date >= date_from)
        if date_to:
            filters.append(AttendanceRecord.attendance_date <= date_to)

        base = select(AttendanceRecord).where(*filters)
        total = (await self.session.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

        rows = (
            await self.session.execute(
                base.order_by(AttendanceRecord.attendance_date.desc()).limit(limit).offset(offset)
            )
        ).scalars().all()
        return rows, total

    async def summary_for_student(self, *, student_id: str, date_from: date | None, date_to: date | None) -> dict:
        filters = [AttendanceRecord.student_id == student_id]
        if date_from:
            filters.append(AttendanceRecord.attendance_date >= date_from)
        if date_to:
            filters.append(AttendanceRecord.attendance_date <= date_to)

        stmt = select(
            func.count().label("total"),
            func.sum(case((AttendanceRecord.status == AttendanceStatus.PRESENT, 1), else_=0)).label("present"),
            func.sum(case((AttendanceRecord.status == AttendanceStatus.ABSENT, 1), else_=0)).label("absent"),
        ).where(*filters)

        row = (await self.session.execute(stmt)).one()
        total = int(row.total or 0)
        present = int(row.present or 0)
        absent = int(row.absent or 0)
        pct = round((present / total) * 100, 2) if total else 0.0
        return {
            "total_days": total,
            "present_days": present,
            "absent_days": absent,
            "attendance_percentage": pct,
        }
