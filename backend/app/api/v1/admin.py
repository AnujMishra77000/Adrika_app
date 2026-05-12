from datetime import date

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_roles
from app.cache.keys import student_content_key
from app.cache.redis_client import get_redis
from app.cache.utils import delete_keys
from app.db.session import get_db_session
from app.schemas.admin import (
    AdminAssessmentAssignDTO,
    AdminAssessmentBuildDTO,
    AdminAssessmentCreateDTO,
    AdminQuestionBankCreateDTO,
    AdminQuestionBankUpdateDTO,
    AdminAttendanceCorrectionApproveDTO,
    AdminAttendanceCorrectionCreateDTO,
    AdminBannerCreateDTO,
    AdminBannerUpdateDTO,
    AdminBatchCreateDTO,
    AdminStandardCreateDTO,
    AdminDailyThoughtUpsertDTO,
    AdminDoubtUpdateDTO,
    AdminHomeworkCreateDTO,
    AdminNoticeCreateDTO,
    AdminNotificationCreateDTO,
    AdminResultPublishDTO,
    AdminResultWhatsappDTO,
    AdminSubjectCreateDTO,
    AdminSubjectEstimateUpsertDTO,
    AdminStudentCreateDTO,
    AdminStudentEnquiryCreateDTO,
    AdminStudentEnquiryUpdateDTO,
    AdminStudentUpdateDTO,
    AdminParentLinkCreateDTO,
    AdminStudentStatusUpdateDTO,
    AdminTeacherCreateDTO,
    AdminTeacherCredentialResetDTO,
    AdminTeacherStatusUpdateDTO,
    AdminStudentCredentialResetDTO,
    AdminFeeStructureCreateDTO,
    AdminFeeStructureUpdateDTO,
    AdminStudentFeePaymentCreateDTO,
    AdminStudentFeeReceiptWhatsappDTO,
    AdminFeeOverdueReminderDTO,
    AdminStudentFeeStructureAssignDTO,
)
from app.schemas.registration import AdminRegistrationDecisionDTO
from app.schemas.suggestion import SuggestionMessageCreateDTO
from app.schemas.lecture_schedule import AdminLectureScheduleCreateDTO, AdminLectureScheduleStatusUpdateDTO
from app.services.admin_assessment_service import AdminAssessmentService
from app.services.admin_homework_service import AdminHomeworkService
from app.services.admin_notice_service import AdminNoticeService
from app.services.admin_service import AdminService
from app.services.lecture_schedule_service import LectureScheduleService
from app.services.notification_service import NotificationService
from app.services.registration_review_service import RegistrationReviewService
from app.services.suggestion_service import SuggestionService
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
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_students(
        search=search,
        status=status,
        class_level=class_level,
        stream=stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/credentials")
async def list_student_credentials(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=0, le=12),
    stream: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_student_credentials(
        search=search,
        status=status,
        class_level=class_level,
        stream=stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/summary")
async def student_summary(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).student_summary()


@router.get("/students/enquiries")
async def list_student_enquiries(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_student_enquiries(limit=limit, offset=offset)
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/enquiries")
async def list_enquiries(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    fee_class_level: int | None = Query(default=None, ge=6, le=12),
    fee_stream: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_admin_enquiries(
        search=search,
        status=status,
        class_level=class_level,
        fee_class_level=fee_class_level,
        fee_stream=fee_stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/enquiries")
async def create_enquiry(
    payload: AdminStudentEnquiryCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_admin_enquiry(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.patch("/enquiries/{enquiry_id}")
async def update_enquiry(
    enquiry_id: str,
    payload: AdminStudentEnquiryUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).update_admin_enquiry(
        enquiry_id=enquiry_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/enquiries/{enquiry_id}/timeline")
async def get_enquiry_timeline(
    enquiry_id: str,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_enquiry_timeline(
        enquiry_id=enquiry_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/details")
async def list_student_details(
    search: str | None = Query(default=None),
    status: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_student_details(
        search=search,
        status=status,
        class_level=class_level,
        stream=stream,
        student_id=None,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/students/{student_id}/report-card")
async def get_student_report_card(
    student_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).get_student_report_card(student_id=student_id)


@router.get("/students/{student_id}/full-profile")
async def get_student_full_profile(
    student_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).get_student_full_profile(student_id=student_id)


@router.get("/students/{student_id}/full-profile/export")
async def export_student_full_profile(
    student_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).export_student_full_profile_pdf(student_id=student_id)


@router.post("/students/{student_id}/report-card/whatsapp")
async def send_student_report_card_whatsapp(
    student_id: str,
    payload: AdminResultWhatsappDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).send_student_report_card_whatsapp(
        student_id=student_id,
        phone=payload.phone,
        custom_message=payload.message,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.patch("/students/{user_id}/status")
async def update_student_status(
    user_id: str,
    payload: AdminStudentStatusUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).update_student(
        user_id=user_id,
        payload=AdminStudentUpdateDTO(status=payload.status),
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


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


@router.post("/students/{student_id}/credentials/reset")
async def reset_student_credentials(
    student_id: str,
    payload: AdminStudentCredentialResetDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).reset_student_credentials(
        student_id=student_id,
        new_password=payload.new_password,
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




@router.post("/standards")
async def create_standard(
    payload: AdminStandardCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_standard(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


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
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_subjects(
        search=search,
        class_level=class_level,
        stream=stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/subjects")
async def create_subject(
    payload: AdminSubjectCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_subject(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/subjects/{subject_id}/estimated-hours")
async def upsert_subject_estimated_hours(
    subject_id: str,
    payload: AdminSubjectEstimateUpsertDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).upsert_subject_estimated_hours(
        subject_id=subject_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/syllabus/completion")
async def syllabus_completion_report(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).syllabus_completion_report()


@router.get("/teachers")
async def list_teachers(
    search: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await LectureScheduleService(session).list_admin_teachers(
        search=search,
        class_level=class_level,
        stream=stream,
        subject_id=subject_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/teachers")
async def create_teacher(
    payload: AdminTeacherCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await LectureScheduleService(session).create_admin_teacher(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/teachers/credentials")
async def list_teacher_credentials(
    search: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await LectureScheduleService(session).list_teacher_credentials(
        search=search,
        class_level=class_level,
        stream=stream,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.patch("/teachers/{teacher_id}/status")
async def update_teacher_status(
    teacher_id: str,
    payload: AdminTeacherStatusUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await LectureScheduleService(session).update_admin_teacher_status(
        teacher_id=teacher_id,
        status=payload.status,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/teachers/{teacher_id}/credentials/reset")
async def reset_teacher_credentials(
    teacher_id: str,
    payload: AdminTeacherCredentialResetDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await LectureScheduleService(session).reset_teacher_credentials(
        teacher_id=teacher_id,
        new_password=payload.new_password,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/teachers/salary-ledger")
async def list_teacher_salary_ledger(
    teacher_id: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total, summary = await LectureScheduleService(session).list_teacher_salary_ledger(
        teacher_id=teacher_id,
        class_level=class_level,
        stream=stream,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "summary": summary, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/teachers/{teacher_id}/salary-slip")
async def get_teacher_salary_slip(
    teacher_id: str,
    from_date: date | None = Query(default=None),
    to_date: date | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await LectureScheduleService(session).get_teacher_salary_slip(
        teacher_id=teacher_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.delete("/teachers/{teacher_id}")
async def delete_teacher(
    teacher_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await LectureScheduleService(session).delete_admin_teacher(
        teacher_id=teacher_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/lecture-schedules")
async def list_lecture_schedules(
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    teacher_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    scheduled_from: date | None = Query(default=None),
    scheduled_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await LectureScheduleService(session).list_admin_schedules(
        class_level=class_level,
        stream=stream,
        subject_id=subject_id,
        teacher_id=teacher_id,
        status=status,
        search=search,
        scheduled_from=scheduled_from,
        scheduled_to=scheduled_to,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/activity-tracker/daily")
async def get_daily_activity_tracker(
    day: date,
    search: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).get_daily_activity_tracker(
        day=day,
        search=search,
    )


@router.post("/lecture-schedules")
async def create_lecture_schedule(
    payload: AdminLectureScheduleCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await LectureScheduleService(session).create_admin_schedule(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/lecture-schedules/{schedule_id}/status")
async def update_lecture_schedule_status(
    schedule_id: str,
    payload: AdminLectureScheduleStatusUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await LectureScheduleService(session).update_admin_schedule_status(
        schedule_id=schedule_id,
        status=payload.status,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/notices")
async def list_notices(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminNoticeService(session).list_notices(status=status, limit=limit, offset=offset)
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/notices")
async def create_notice(
    payload: AdminNoticeCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminNoticeService(session).create_notice(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/notices/{notice_id}/publish")
async def publish_notice(
    notice_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminNoticeService(session, cache).publish_notice(
        notice_id=notice_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/notices/{notice_id}/attachments")
async def upload_notice_attachment(
    notice_id: str,
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminNoticeService(session, cache).upload_notice_attachment(
        notice_id=notice_id,
        file=file,
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
    items, total = await AdminHomeworkService(session).list_homework(
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
    return await AdminHomeworkService(session).create_homework(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/homework/{homework_id}/publish")
async def publish_homework(
    homework_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminHomeworkService(session, cache).publish_homework(
        homework_id=homework_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/homework/completions")
async def list_homework_completions(
    homework_id: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminHomeworkService(session).list_homework_completions(
        homework_id=homework_id,
        class_level=class_level,
        stream=stream,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/homework/{homework_id}/attachments")
async def upload_homework_attachment(
    homework_id: str,
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminHomeworkService(session, cache).upload_homework_attachment(
        homework_id=homework_id,
        file=file,
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


@router.get("/assessments/question-bank")
async def list_saved_test_questions(
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    topic: str | None = Query(default=None),
    search: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminAssessmentService(session).list_saved_questions(
        class_level=class_level,
        stream=stream,
        subject_id=subject_id,
        topic=topic,
        search=search,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/assessments/question-bank")
async def create_saved_test_question(
    payload: AdminQuestionBankCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminAssessmentService(session).create_saved_question(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.patch("/assessments/question-bank/{question_id}")
async def update_saved_test_question(
    question_id: str,
    payload: AdminQuestionBankUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminAssessmentService(session).update_saved_question(
        question_id=question_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.delete("/assessments/question-bank/{question_id}")
async def delete_saved_test_question(
    question_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminAssessmentService(session).delete_saved_question(
        question_id=question_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/assessments/create-test")
async def create_test(
    payload: AdminAssessmentBuildDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminAssessmentService(session).create_test(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.post("/assessments/{assessment_id}/assign")
async def assign_test(
    assessment_id: str,
    payload: AdminAssessmentAssignDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminAssessmentService(session, cache).assign_test(
        assessment_id=assessment_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/assessments/{assessment_id}/questions")
async def list_test_questions(
    assessment_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminAssessmentService(session).list_test_questions(assessment_id=assessment_id)


@router.get("/results/topics")
async def list_result_topics(
    class_level: int = Query(..., ge=6, le=12),
    stream: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_result_topics(
        class_level=class_level,
        stream=stream,
        subject_id=subject_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/results/topics/{assessment_id}/students")
async def list_result_topic_students(
    assessment_id: str,
    search: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    payload = await AdminService(session).list_result_topic_students(
        assessment_id=assessment_id,
        search=search,
        limit=limit,
        offset=offset,
    )
    return {
        "assessment": payload["assessment"],
        "items": payload["items"],
        "meta": build_meta(total=payload["total"], limit=limit, offset=offset),
    }


@router.post("/results/topics/{assessment_id}/students/{student_id}/whatsapp")
async def send_result_to_parent_whatsapp(
    assessment_id: str,
    student_id: str,
    payload: AdminResultWhatsappDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).send_student_result_whatsapp(
        assessment_id=assessment_id,
        student_id=student_id,
        payload=payload,
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



@router.get("/doubts/{doubt_id}/conversation")
async def doubt_conversation(
    doubt_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).get_doubt_conversation(doubt_id=doubt_id)
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


@router.get("/suggestions/unread-count")
async def suggestion_unread_count(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await SuggestionService(session).admin_unread_count()


@router.get("/suggestions/threads")
async def list_suggestion_threads(
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await SuggestionService(session).admin_list_threads(
        search=search,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.get("/suggestions/threads/{thread_id}/messages")
async def get_suggestion_thread_messages(
    thread_id: str,
    limit: int = Query(default=300, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    payload = await SuggestionService(session).admin_get_thread_messages(
        thread_id=thread_id,
        limit=limit,
        offset=offset,
    )
    return {
        "thread": payload["thread"],
        "items": payload["items"],
        "meta": build_meta(total=payload["total"], limit=limit, offset=offset),
    }


@router.post("/suggestions/threads/{thread_id}/messages")
async def admin_send_suggestion_message(
    thread_id: str,
    payload: SuggestionMessageCreateDTO,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await SuggestionService(session).admin_send_message(
        thread_id=thread_id,
        admin_user_id=current_user.id,
        message=payload.message,
    )


@router.get("/banners")
async def list_banners(
    active_on: date | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_banners(
        active_on=active_on,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/banners/upload")
async def upload_banner_image(
    request: Request,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).upload_banner_image(
        file=file,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


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
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    return await NotificationService(session, cache).send_to_targets(
        title=payload.title,
        body=payload.body,
        notification_type=payload.notification_type,
        targets=[target.model_dump() for target in payload.targets],
        metadata={
            "source": payload.notification_type,
            "attachments": [item.model_dump() for item in payload.attachments],
        },
        actor_user_id=current_user.id,
        audit_action="admin.notification.create",
        audit_ip_address=_client_ip(request),
    )


@router.post("/notifications/attachments")
async def upload_notification_attachment(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    _ = current_user
    _ = cache
    return await NotificationService(session, cache).upload_attachment(file=file)


@router.get("/notifications/history")
async def list_notification_history(
    title: str | None = Query(default=None),
    on_date: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    cache: Redis = Depends(get_redis),
    current_user=Depends(get_current_user),
) -> dict:
    _ = current_user
    service = NotificationService(session, cache)
    items, total = await service.list_broadcast_history(
        limit=limit,
        offset=offset,
        title_query=title,
        on_date=on_date,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


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



@router.get("/fees/summary")
async def fee_summary(
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).fee_summary()


@router.get("/fees/monthly-analytics")
async def fee_monthly_analytics(
    months: int = Query(default=12, ge=3, le=24),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).fee_monthly_analytics(months=months, month=month)


@router.get("/fees/structures")
async def list_fee_structures(
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_fee_structures(
        class_level=class_level,
        stream=stream,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/fees/structures")
async def create_fee_structure(
    payload: AdminFeeStructureCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).create_fee_structure(
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.patch("/fees/structures/{structure_id}")
async def update_fee_structure(
    structure_id: str,
    payload: AdminFeeStructureUpdateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).update_fee_structure(
        structure_id=structure_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.delete("/fees/structures/{structure_id}")
async def delete_fee_structure(
    structure_id: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).delete_fee_structure(
        structure_id=structure_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )


@router.get("/fees/students")
async def list_fee_students(
    view: str = Query(default="all", pattern="^(all|pending|paid)$"),
    search: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_fee_students(
        view=view,
        search=search,
        class_level=class_level,
        stream=stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}




@router.get("/fees/students/{student_id}/assignment")
async def get_student_fee_assignment(
    student_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).get_student_fee_assignment(student_id=student_id)


@router.put("/fees/students/{student_id}/assignment")
async def assign_student_fee_structure(
    student_id: str,
    payload: AdminStudentFeeStructureAssignDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).assign_student_fee_structure(
        student_id=student_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )




@router.post("/fees/students/{student_id}/payments")
async def record_student_fee_payment(
    student_id: str,
    payload: AdminStudentFeePaymentCreateDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).record_student_fee_payment(
        student_id=student_id,
        payload=payload,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
    )

@router.get("/fees/students/{student_id}/receipt/latest")
async def get_student_fee_receipt(
    student_id: str,
    regenerate: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    return await AdminService(session).get_student_fee_receipt(
        student_id=student_id,
        regenerate=regenerate,
    )


@router.post("/fees/students/{student_id}/receipt/latest/whatsapp")
async def send_student_fee_receipt_whatsapp(
    student_id: str,
    payload: AdminStudentFeeReceiptWhatsappDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).send_student_fee_receipt_whatsapp(
        student_id=student_id,
        actor_user_id=current_user.id,
        ip_address=_client_ip(request),
        phone_override=payload.phone,
        custom_message=payload.message,
    )


@router.get("/fees/overdue")
async def list_fee_overdue_students(
    search: str | None = Query(default=None),
    class_level: int | None = Query(default=None, ge=6, le=12),
    stream: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    items, total = await AdminService(session).list_fee_overdue_students(
        search=search,
        class_level=class_level,
        stream=stream,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "meta": build_meta(total=total, limit=limit, offset=offset)}


@router.post("/fees/reminders/overdue")
async def send_fee_overdue_reminders(
    payload: AdminFeeOverdueReminderDTO,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
) -> dict:
    return await AdminService(session).send_fee_overdue_reminders(
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
