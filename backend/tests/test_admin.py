from datetime import UTC, date, datetime, timedelta

import pytest
from httpx import AsyncClient


async def _login_token(client: AsyncClient, identifier: str, password: str, device_id: str) -> str:
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


@pytest.mark.anyio
async def test_admin_endpoint_requires_admin_role(client: AsyncClient) -> None:
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student")

    response = await client.get(
        "/api/v1/admin/students",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_admin_can_create_and_publish_notice(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin")

    create_response = await client.post(
        "/api/v1/admin/notices",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Admin Notice",
            "body": "Important update",
            "priority": 5,
            "targets": [{"target_type": "all_students", "target_id": "all"}],
        },
    )
    assert create_response.status_code == 200
    notice_id = create_response.json()["id"]

    publish_response = await client.post(
        f"/api/v1/admin/notices/{notice_id}/publish",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"
    assert publish_response.json()["recipient_count"] >= 1

    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-notice")
    notifications_response = await client.get(
        "/api/v1/students/me/notifications?limit=20&offset=0",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert notifications_response.status_code == 200
    assert any(
        item["title"] == "Admin Notice" and item.get("source") == "notice"
        for item in notifications_response.json()["items"]
    )


@pytest.mark.anyio
async def test_admin_can_upsert_daily_thought_and_list_subjects(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-2")

    upsert_response = await client.put(
        "/api/v1/admin/daily-thoughts",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "thought_date": date.today().isoformat(),
            "text": "Phase 2 operational control is live.",
            "is_active": True,
        },
    )
    assert upsert_response.status_code == 200
    assert upsert_response.json()["thought_date"] == date.today().isoformat()

    subjects_response = await client.get(
        "/api/v1/admin/subjects?limit=20&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert subjects_response.status_code == 200

    codes = {item["code"] for item in subjects_response.json()["items"]}
    assert "MATH" in codes


@pytest.mark.anyio
async def test_admin_can_create_banner_and_list_banners(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-3")

    now = datetime.now(UTC)
    create_response = await client.post(
        "/api/v1/admin/banners",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Admissions Open",
            "media_url": "https://cdn.adr.local/banner.png",
            "action_url": "https://adr.local/admissions",
            "active_from": now.isoformat(),
            "active_to": (now + timedelta(days=7)).isoformat(),
            "priority": 10,
            "is_popup": True,
        },
    )
    assert create_response.status_code == 200

    list_response = await client.get(
        "/api/v1/admin/banners?limit=20&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_response.status_code == 200
    titles = {item["title"] for item in list_response.json()["items"]}
    assert "Admissions Open" in titles


@pytest.mark.anyio
async def test_admin_student_status_toggle_blocks_access_immediately(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-status")
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-status")

    headers = {"Authorization": f"Bearer {admin_token}"}

    students_response = await client.get("/api/v1/admin/students?limit=20&offset=0", headers=headers)
    assert students_response.status_code == 200
    student = students_response.json()["items"][0]

    deactivate_response = await client.patch(
        f"/api/v1/admin/students/{student['user_id']}/status",
        headers=headers,
        json={"status": "inactive"},
    )
    assert deactivate_response.status_code == 200
    assert deactivate_response.json()["status"] == "inactive"

    # Existing access token should also be blocked immediately by dependencies guard.
    student_dashboard_response = await client.get(
        "/api/v1/students/me/dashboard",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert student_dashboard_response.status_code == 401

    # New login attempts must fail while inactive.
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "student@test.local",
            "password": "Student@123",
            "device": {
                "device_id": "device-student-status-2",
                "platform": "android",
                "app_version": "1.0.0",
            },
        },
    )
    assert login_response.status_code == 401




@pytest.mark.anyio
async def test_admin_fee_structure_crud_and_student_views(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-fee")
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_response = await client.post(
        "/api/v1/admin/fees/structures",
        headers=headers,
        json={
            "name": "Class 10 Standard Plan",
            "class_level": 10,
            "stream": None,
            "total_amount": 30000,
            "installment_count": 3,
            "description": "Base fee plan for class 10",
            "is_active": True,
        },
    )
    assert create_response.status_code == 200
    structure_id = create_response.json()["id"]

    list_response = await client.get(
        "/api/v1/admin/fees/structures?limit=50&offset=0",
        headers=headers,
    )
    assert list_response.status_code == 200
    assert any(item["id"] == structure_id for item in list_response.json()["items"])

    update_response = await client.patch(
        f"/api/v1/admin/fees/structures/{structure_id}",
        headers=headers,
        json={
            "name": "Class 10 Revised Plan",
            "class_level": 10,
            "stream": None,
            "total_amount": 36000,
            "installment_count": 4,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["class_level"] == 10
    assert update_response.json()["stream"] is None

    pending_students_response = await client.get(
        "/api/v1/admin/fees/students?view=pending&limit=50&offset=0",
        headers=headers,
    )
    assert pending_students_response.status_code == 200
    assert pending_students_response.json()["meta"]["total"] == 0

    paid_students_response = await client.get(
        "/api/v1/admin/fees/students?view=paid&limit=50&offset=0",
        headers=headers,
    )
    assert paid_students_response.status_code == 200
    assert paid_students_response.json()["meta"]["total"] == 0

    delete_response = await client.delete(
        f"/api/v1/admin/fees/structures/{structure_id}",
        headers=headers,
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


@pytest.mark.anyio
async def test_admin_can_assign_fee_structure_to_student_and_reflect_in_student_list(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-fee-assign")
    headers = {"Authorization": f"Bearer {admin_token}"}

    students_response = await client.get(
        "/api/v1/admin/fees/students?view=all&limit=50&offset=0",
        headers=headers,
    )
    assert students_response.status_code == 200
    students = students_response.json()["items"]
    assert len(students) >= 1
    student_id = students[0]["student_id"]

    create_structure_response = await client.post(
        "/api/v1/admin/fees/structures",
        headers=headers,
        json={
            "name": "Class 10 Assignment Plan",
            "class_level": 10,
            "stream": None,
            "total_amount": 42000,
            "installment_count": 4,
            "description": "Assignment-ready class 10 structure",
            "is_active": True,
        },
    )
    assert create_structure_response.status_code == 200
    structure_id = create_structure_response.json()["id"]

    assignment_get_response = await client.get(
        f"/api/v1/admin/fees/students/{student_id}/assignment",
        headers=headers,
    )
    assert assignment_get_response.status_code == 200
    assignment_payload = assignment_get_response.json()
    assert assignment_payload["student"]["student_id"] == student_id
    assert any(item["id"] == structure_id for item in assignment_payload["available_structures"])

    assignment_put_response = await client.put(
        f"/api/v1/admin/fees/students/{student_id}/assignment",
        headers=headers,
        json={"fee_structure_id": structure_id},
    )
    assert assignment_put_response.status_code == 200
    assert assignment_put_response.json()["assigned"] is True
    assert assignment_put_response.json()["fee_structure_id"] == structure_id

    list_after_assign = await client.get(
        "/api/v1/admin/fees/students?view=all&limit=50&offset=0",
        headers=headers,
    )
    assert list_after_assign.status_code == 200

    assigned_row = next(item for item in list_after_assign.json()["items"] if item["student_id"] == student_id)
    assert assigned_row["fee_structure_assigned"] is True
    assert assigned_row["fee_structure_id"] == structure_id
    assert assigned_row["fee_amount"] == 42000.0
    assert assigned_row["stream"] == "general science"


@pytest.mark.anyio
async def test_admin_can_record_fee_payment_and_move_student_to_paid_list(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-fee-payment")
    headers = {"Authorization": f"Bearer {admin_token}"}

    students_response = await client.get(
        "/api/v1/admin/fees/students?view=all&limit=50&offset=0",
        headers=headers,
    )
    assert students_response.status_code == 200
    student_id = students_response.json()["items"][0]["student_id"]

    create_structure_response = await client.post(
        "/api/v1/admin/fees/structures",
        headers=headers,
        json={
            "name": "Class 10 Full Payment Plan",
            "class_level": 10,
            "stream": None,
            "total_amount": 3000,
            "installment_count": 3,
            "description": "Payment flow verification",
            "is_active": True,
        },
    )
    assert create_structure_response.status_code == 200
    structure_id = create_structure_response.json()["id"]

    assign_response = await client.put(
        f"/api/v1/admin/fees/students/{student_id}/assignment",
        headers=headers,
        json={"fee_structure_id": structure_id},
    )
    assert assign_response.status_code == 200

    assignment_details = await client.get(
        f"/api/v1/admin/fees/students/{student_id}/assignment",
        headers=headers,
    )
    assert assignment_details.status_code == 200
    pending_before = assignment_details.json()["billing"]["pending_amount"]
    assert pending_before > 0

    payment_response = await client.post(
        f"/api/v1/admin/fees/students/{student_id}/payments",
        headers=headers,
        json={
            "amount": pending_before,
            "paid_on": date.today().isoformat(),
            "payment_mode": "upi",
            "reference_no": "TXN-TEST-001",
            "period_label": "Final Installment",
            "note": "Cleared outstanding fee",
        },
    )
    assert payment_response.status_code == 200
    payment_payload = payment_response.json()
    assert payment_payload["billing"]["pending_amount"] == 0
    assert payment_payload["billing"]["is_fully_paid"] is True

    paid_view_response = await client.get(
        "/api/v1/admin/fees/students?view=paid&limit=50&offset=0",
        headers=headers,
    )
    assert paid_view_response.status_code == 200

    paid_row = next(item for item in paid_view_response.json()["items"] if item["student_id"] == student_id)
    assert paid_row["is_fully_paid"] is True
    assert paid_row["payment_status"] == "paid"

    pending_view_response = await client.get(
        "/api/v1/admin/fees/students?view=pending&limit=50&offset=0",
        headers=headers,
    )
    assert pending_view_response.status_code == 200
    assert all(item["student_id"] != student_id for item in pending_view_response.json()["items"])

    receipt_response = await client.get(
        f"/api/v1/admin/fees/students/{student_id}/receipt/latest",
        headers=headers,
    )
    assert receipt_response.status_code == 200
    receipt_payload = receipt_response.json()
    assert receipt_payload["receipt"]["file_name"].endswith(".pdf")
    assert receipt_payload["receipt"]["download_url"].startswith("/media/receipts/")

    whatsapp_response = await client.post(
        f"/api/v1/admin/fees/students/{student_id}/receipt/latest/whatsapp",
        headers=headers,
        json={"phone": "919000000004"},
    )
    assert whatsapp_response.status_code == 200
    assert whatsapp_response.json()["delivery"]["status"] in {"mock_sent", "sent", "failed"}


@pytest.mark.anyio
async def test_admin_homework_publish_with_attachment_reaches_student_and_marks_read(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-homework")
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-homework")

    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}

    subjects_response = await client.get(
        "/api/v1/admin/subjects?limit=20&offset=0",
        headers=admin_headers,
    )
    assert subjects_response.status_code == 200
    subjects = subjects_response.json()["items"]
    assert len(subjects) >= 1
    subject_id = subjects[0]["id"]

    title = f"Homework {datetime.now(UTC).timestamp()}"
    due_at = (datetime.now(UTC) + timedelta(hours=4)).isoformat()

    create_response = await client.post(
        "/api/v1/admin/homework",
        headers=admin_headers,
        json={
            "title": title,
            "description": "Complete chapter exercises and submit working notes.",
            "subject_id": subject_id,
            "due_at": due_at,
            "targets": [{"target_type": "all_students", "target_id": "all"}],
        },
    )
    assert create_response.status_code == 200
    payload = create_response.json()
    homework_id = payload["id"]
    assert payload["status"] == "draft"
    assert payload["generated_attachment_id"]

    sample_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF\n"
    upload_response = await client.post(
        f"/api/v1/admin/homework/{homework_id}/attachments",
        headers=admin_headers,
        files={"file": ("worksheet.pdf", sample_pdf, "application/pdf")},
    )
    assert upload_response.status_code == 200
    assert upload_response.json()["content_type"] == "application/pdf"

    publish_response = await client.post(
        f"/api/v1/admin/homework/{homework_id}/publish",
        headers=admin_headers,
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["status"] == "published"
    assert publish_response.json()["recipient_count"] >= 1

    student_homework_response = await client.get(
        "/api/v1/students/me/homework?limit=100&offset=0",
        headers=student_headers,
    )
    assert student_homework_response.status_code == 200
    homework_items = student_homework_response.json()["items"]
    student_homework = next(item for item in homework_items if item["id"] == homework_id)
    assert student_homework["title"] == title
    assert student_homework["is_read"] is False
    assert student_homework["attachment_count"] >= 2
    assert len(student_homework["attachments"]) >= 2

    notifications_response = await client.get(
        "/api/v1/students/me/notifications?limit=100&offset=0",
        headers=student_headers,
    )
    assert notifications_response.status_code == 200
    assert any(
        item["title"] == title and item.get("source") == "homework"
        for item in notifications_response.json()["items"]
    )

    mark_seen_response = await client.post(
        "/api/v1/students/me/homework/read-all",
        headers=student_headers,
    )
    assert mark_seen_response.status_code == 200
    assert mark_seen_response.json()["marked_count"] >= 1

    student_homework_after_read = await client.get(
        "/api/v1/students/me/homework?limit=100&offset=0",
        headers=student_headers,
    )
    assert student_homework_after_read.status_code == 200
    homework_items_after_read = student_homework_after_read.json()["items"]
    updated = next(item for item in homework_items_after_read if item["id"] == homework_id)
    assert updated["is_read"] is True
