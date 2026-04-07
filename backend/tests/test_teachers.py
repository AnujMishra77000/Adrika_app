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
async def test_teacher_endpoint_requires_teacher_role(client: AsyncClient) -> None:
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-teacher")

    response = await client.get(
        "/api/v1/teachers/me/profile",
        headers={"Authorization": f"Bearer {student_token}"},
    )

    assert response.status_code == 403


@pytest.mark.anyio
async def test_teacher_can_use_phase3_apis(client: AsyncClient) -> None:
    teacher_token = await _login_token(client, "teacher@test.local", "Teacher@123", "device-teacher")
    headers = {"Authorization": f"Bearer {teacher_token}"}

    profile_response = await client.get("/api/v1/teachers/me/profile", headers=headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["full_name"] == "Test Teacher"

    dashboard_response = await client.get("/api/v1/teachers/me/dashboard", headers=headers)
    assert dashboard_response.status_code == 200
    dashboard = dashboard_response.json()
    assert dashboard["assigned_batches_count"] == 1
    assert dashboard["assigned_subjects_count"] == 1

    assignment_response = await client.get("/api/v1/teachers/me/assignments", headers=headers)
    assert assignment_response.status_code == 200
    assert len(assignment_response.json()["items"]) == 1

    notices_response = await client.get("/api/v1/teachers/me/notices", headers=headers)
    assert notices_response.status_code == 200
    notices = notices_response.json()["items"]
    assert len(notices) >= 1

    notice_id = notices[0]["id"]
    mark_notice = await client.post(f"/api/v1/teachers/me/notices/{notice_id}/read", headers=headers)
    assert mark_notice.status_code == 200

    homework_response = await client.get("/api/v1/teachers/me/homework", headers=headers)
    assert homework_response.status_code == 200
    assert len(homework_response.json()["items"]) >= 1

    tests_response = await client.get("/api/v1/teachers/me/tests", headers=headers)
    assert tests_response.status_code == 200
    assert len(tests_response.json()["items"]) >= 1

    doubts_response = await client.get("/api/v1/teachers/me/doubts", headers=headers)
    assert doubts_response.status_code == 200
    doubts = doubts_response.json()["items"]
    assert len(doubts) >= 1

    doubt_id = doubts[0]["id"]
    doubt_detail = await client.get(f"/api/v1/teachers/me/doubts/{doubt_id}", headers=headers)
    assert doubt_detail.status_code == 200
    assert doubt_detail.json()["doubt"]["topic"] == "Factorization"

    message_response = await client.post(
        f"/api/v1/teachers/me/doubts/{doubt_id}/messages",
        headers=headers,
        json={"message": "Let's solve this by splitting the middle term."},
    )
    assert message_response.status_code == 200

    status_response = await client.post(
        f"/api/v1/teachers/me/doubts/{doubt_id}/status",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "in_progress"

    notifications_response = await client.get("/api/v1/teachers/me/notifications", headers=headers)
    assert notifications_response.status_code == 200
    assert notifications_response.json()["unread_count"] >= 1

    read_all_response = await client.post("/api/v1/teachers/me/notifications/read-all", headers=headers)
    assert read_all_response.status_code == 200
