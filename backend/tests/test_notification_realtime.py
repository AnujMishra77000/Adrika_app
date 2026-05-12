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
async def test_device_registration_and_notification_send_flow(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-notif")
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-notif")

    register_response = await client.post(
        "/api/v1/devices/register",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "device_id": "android-student-1",
            "platform": "android",
            "push_token": "tok_student_12345678901234567890",
            "app_version": "1.0.0",
        },
    )
    assert register_response.status_code == 200
    assert register_response.json()["is_active"] is True

    send_response = await client.post(
        "/api/v1/notifications/send",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Class Alert",
            "body": "Tomorrow test at 8 AM",
            "notification_type": "test",
            "targets": [{"target_type": "all_students", "target_id": "all"}],
            "metadata": {"source": "test"},
        },
    )
    assert send_response.status_code == 200
    assert send_response.json()["recipient_count"] >= 1

    list_response = await client.get(
        "/api/v1/notifications?limit=20&offset=0",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert list_response.status_code == 200
    assert any(item["title"] == "Class Alert" for item in list_response.json()["items"])
    assert list_response.json()["unread_count"] >= 1

    unread_response = await client.get(
        "/api/v1/notifications/unread-count",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert unread_response.status_code == 200
    assert unread_response.json()["unread_count"] >= 1

    target_notification = next(
        item for item in list_response.json()["items"] if item["title"] == "Class Alert"
    )
    read_response = await client.post(
        f"/api/v1/notifications/{target_notification['id']}/read",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert read_response.status_code == 200
    assert "unread_count" in read_response.json()

    read_all_response = await client.post(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert read_all_response.status_code == 200
    assert read_all_response.json()["unread_count"] == 0


@pytest.mark.anyio
async def test_notification_send_requires_teacher_or_admin_role(client: AsyncClient) -> None:
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-blocked")

    send_response = await client.post(
        "/api/v1/notifications/send",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "title": "Unauthorized",
            "body": "This should fail",
            "notification_type": "system",
            "targets": [{"target_type": "all_students", "target_id": "all"}],
        },
    )
    assert send_response.status_code == 403
