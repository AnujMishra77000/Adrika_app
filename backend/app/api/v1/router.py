from fastapi import APIRouter

from app.api.v1 import (
    admin,
    assessments,
    attendance,
    auth,
    doubts,
    homework,
    notices,
    notifications,
    parents,
    results,
    students,
    teachers,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(students.router)
api_router.include_router(teachers.router)
api_router.include_router(parents.router)
api_router.include_router(notices.router)
api_router.include_router(homework.router)
api_router.include_router(attendance.router)
api_router.include_router(assessments.router)
api_router.include_router(results.router)
api_router.include_router(doubts.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
