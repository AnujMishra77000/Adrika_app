from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.cache.keys import student_content_key
from app.cache.redis_client import get_redis
from app.cache.utils import delete_keys
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminAssessmentCreateDTO,
    AdminAttendanceCorrectionApproveDTO,
    AdminAttendanceCorrectionCreateDTO,
    AdminBannerCreateDTO,
    AdminBannerUpdateDTO,
    AdminBatchCreateDTO,
    AdminDailyThoughtUpsertDTO,
    AdminDoubtUpdateDTO,
    AdminHomeworkCreateDTO,
    AdminNoticeCreateDTO,
    AdminNotificationCreateDTO,
    AdminResultPublishDTO,
    AdminStudentCreateDTO,
    AdminStudentUpdateDTO,
    AdminParentLinkCreateDTO,
    AdminFeeInvoiceCreateDTO,
    AdminPaymentReconcileDTO,
)
from app.schemas.registration import AdminRegistrationDecisionDTO
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.registration_review_service import RegistrationReviewService
from app.utils.pagination import build_meta

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_roles("admin"))])


def _client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None


@router.get("/students")
async def list_students(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_students(
        search=search,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/students")
async def create_student(
    payload: AdminStudentCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_student(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.patch("/students/{user_id}")
async def update_student(
    user_id: str,
    payload: AdminStudentUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).update_student(
        user_id=user_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/registration-requests")
async def list_registration_requests(
    status: str = Query(default="pending"),
    role: str = Query(default="all"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await RegistrationReviewService(session).list_requests(
        status=status,
        role=role,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/registration-requests/{request_id}/decision")
async def decide_registration_request(
    request_id: str,
    payload: AdminRegistrationDecisionDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await RegistrationReviewService(session).decide_request(
        request_id=request_id,
        status=payload.status,
        note=payload.note,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/standards")
async def list_standards(
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_standards(limit=limit, offset=offset)
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/batches")
async def list_batches(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_batches(limit=limit, offset=offset)
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/batches")
async def create_batch(
    payload: AdminBatchCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_batch(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/subjects")
async def list_subjects(
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_subjects(search=search, limit=limit, offset=offset)
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/notices")
async def list_notices(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_notices(status=status, limit=limit, offset=offset)
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/notices")
async def create_notice(
    payload: AdminNoticeCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_notice(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/notices/{notice_id}/publish")
async def publish_notice(
    notice_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).publish_notice(
        notice_id=notice_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/homework")
async def list_homework(
    status: str | None = Query(default=None),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_homework(
        status=status,
        due_from=due_from,
        due_to=due_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/homework")
async def create_homework(
    payload: AdminHomeworkCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_homework(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/homework/{homework_id}/publish")
async def publish_homework(
    homework_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).publish_homework(
        homework_id=homework_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/attendance")
async def list_attendance(
    batch_id: str | None = Query(default=None),
    attendance_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_attendance(
        batch_id=batch_id,
        attendance_date=attendance_date,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/attendance/corrections")
async def list_attendance_corrections(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_attendance_corrections(
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/attendance/corrections")
async def create_attendance_correction(
    payload: AdminAttendanceCorrectionCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_attendance_correction(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/attendance/corrections/{correction_id}/decision")
async def decide_attendance_correction(
    correction_id: str,
    payload: AdminAttendanceCorrectionApproveDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).decide_attendance_correction(
        correction_id=correction_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/assessments")
async def list_assessments(
    status: str | None = Query(default=None),
    assessment_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_assessments(
        status=status,
        assessment_type=assessment_type,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/assessments")
async def create_assessment(
    payload: AdminAssessmentCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_assessment(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/assessments/{assessment_id}/publish")
async def publish_assessment(
    assessment_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).publish_assessment(
        assessment_id=assessment_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/results")
async def list_results(
    assessment_id: str | None = Query(default=None),
    batch_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_results(
        assessment_id=assessment_id,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/results/publish")
async def publish_result(
    payload: AdminResultPublishDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).publish_result(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/doubts")
async def list_doubts(
    status: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_doubts(
        status=status,
        subject_id=subject_id,
        query=q,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.patch("/doubts/{doubt_id}")
async def update_doubt(
    doubt_id: str,
    payload: AdminDoubtUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).update_doubt(
        doubt_id=doubt_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/banners")
async def list_banners(
    active_on: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_banners(active_on=active_on, limit=limit, offset=offset)
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/banners")
async def create_banner(
    payload: AdminBannerCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    result = await AdminService(session).create_banner(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )
    await delete_keys(cache, [student_content_key()])
    return result


@router.patch("/banners/{banner_id}")
async def update_banner(
    banner_id: str,
    payload: AdminBannerUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    result = await AdminService(session).update_banner(
        banner_id=banner_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )
    await delete_keys(cache, [student_content_key()])
    return result


@router.get("/daily-thoughts")
async def list_daily_thoughts(
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_daily_thoughts(
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.put("/daily-thoughts")
async def upsert_daily_thought(
    payload: AdminDailyThoughtUpsertDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    result = await AdminService(session).upsert_daily_thought(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )
    await delete_keys(cache, [student_content_key()])
    return result


@router.post("/notifications")
async def create_notification(
    payload: AdminNotificationCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_notification(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/me/notifications")
async def list_my_notifications(
    is_read: bool | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    service = NotificationService(session, cache)
    items, total = await service.list_for_user(
        user_id=current_user.id,
        is_read=is_read,
        limit=limit,
        offset=offset,
    )
    unread_count = await service.unread_count(user_id=current_user.id)
    return {
        "items": items,
        "meta": build_meta(total=total, limit=limit, offset=offset),
        "unread_count": unread_count,
    }


@router.post("/me/notifications/{notification_id}/read")
async def mark_my_notification_read(
    notification_id: str,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    service = NotificationService(session, cache)
    await service.mark_read(user_id=current_user.id, notification_id=notification_id)
    unread_count = await service.unread_count(user_id=current_user.id)
    return {"message": "Marked as read", "unread_count": unread_count}


@router.post("/me/notifications/read-all")
async def mark_all_my_notifications_read(
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    service = NotificationService(session, cache)
    await service.mark_all_read(user_id=current_user.id)
    unread_count = await service.unread_count(user_id=current_user.id)
    return {"message": "All notifications marked as read", "unread_count": unread_count}


@router.get("/parents")
async def list_parents(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_parents(
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/parents/{parent_id}/links")
async def list_parent_links(
    parent_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_parent_links(
        parent_id=parent_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/parents/links")
async def create_parent_link(
    payload: AdminParentLinkCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_parent_link(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/fee-invoices")
async def list_fee_invoices(
    student_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_fee_invoices_admin(
        student_id=student_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/fee-invoices")
async def create_fee_invoice(
    payload: AdminFeeInvoiceCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_fee_invoice(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/payments")
async def list_payments(
    student_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_payments_admin(
        student_id=student_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.patch("/payments/{payment_id}/reconcile")
async def reconcile_payment(
    payment_id: str,
    payload: AdminPaymentReconcileDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).reconcile_payment(
        payment_id=payment_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/audit-logs")
async def list_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_audit_logs(
        action=action,
        entity_type=entity_type,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}
