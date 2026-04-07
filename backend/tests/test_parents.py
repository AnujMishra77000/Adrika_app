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
async def test_parent_endpoint_requires_parent_role(client: AsyncClient) -> None:
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-parent")

    response = await client.get(
        "/api/v1/parents/me/profile",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_parent_can_use_phase4_apis(client: AsyncClient) -> None:
    parent_token = await _login_token(client, "parent@test.local", "Parent@123", "device-parent")
    headers = {"Authorization": f"Bearer {parent_token}"}

    profile_response = await client.get("/api/v1/parents/me/profile", headers=headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["full_name"] == "Test Parent"

    students_response = await client.get("/api/v1/parents/me/students", headers=headers)
    assert students_response.status_code == 200
    students = students_response.json()["items"]
    assert len(students) == 1
    student_id = students[0]["student_id"]

    dashboard_response = await client.get(f"/api/v1/parents/me/dashboard?student_id={student_id}", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["student_id"] == student_id
    assert dashboard["pending_fee_invoices"] >= 1

    notices_response = await client.get(f"/api/v1/parents/me/students/{student_id}/notices", headers=headers)
    assert notices_response.status_code == 200
    notices = notices_response.json()["items"]
    assert len(notices) >= 1

    notice_id = notices[0]["id"]
    notice_detail = await client.get(f"/api/v1/parents/me/students/{student_id}/notices/{notice_id}", headers=headers)
    assert notice_detail.status_code == 200

    read_notice = await client.post(
        f"/api/v1/parents/me/students/{student_id}/notices/{notice_id}/read",
        headers=headers,
    )
    assert read_notice.status_code == 200

    homework_response = await client.get(f"/api/v1/parents/me/students/{student_id}/homework", headers=headers)
    assert homework_response.status_code == 200
    assert len(homework_response.json()["items"]) >= 1

    attendance_response = await client.get(f"/api/v1/parents/me/students/{student_id}/attendance", headers=headers)
    assert attendance_response.status_code == 200
    assert attendance_response.json()["summary"]["total_days"] >= 1

    results_response = await client.get(f"/api/v1/parents/me/students/{student_id}/results", headers=headers)
    assert results_response.status_code == 200
    assert len(results_response.json()["items"]) >= 1

    progress_response = await client.get(f"/api/v1/parents/me/students/{student_id}/progress", headers=headers)
    assert progress_response.status_code == 200
    assert len(progress_response.json()["items"]) >= 1

    fees_response = await client.get(f"/api/v1/parents/me/students/{student_id}/fees", headers=headers)
    assert fees_response.status_code == 200
    assert len(fees_response.json()["items"]) >= 1

    payments_response = await client.get(f"/api/v1/parents/me/students/{student_id}/payments", headers=headers)
    assert payments_response.status_code == 200
    assert len(payments_response.json()["items"]) >= 1

    get_pref = await client.get("/api/v1/parents/me/preferences", headers=headers)
    assert get_pref.status_code == 200

    update_pref = await client.put(
        "/api/v1/parents/me/preferences",
        headers=headers,
        json={
            "in_app_enabled": True,
            "push_enabled": False,
            "whatsapp_enabled": True,
            "fee_reminders_enabled": True,
            "preferred_language": "en",
        },
    )
    assert update_pref.status_code == 200
    assert update_pref.json()["push_enabled"] is False
    assert update_pref.json()["whatsapp_enabled"] is True

    notifications_response = await client.get("/api/v1/parents/me/notifications", headers=headers)
    assert notifications_response.status_code == 200
    assert notifications_response.json()["unread_count"] >= 1

    read_all_response = await client.post("/api/v1/parents/me/notifications/read-all", headers=headers)
    assert read_all_response.status_code == 200
