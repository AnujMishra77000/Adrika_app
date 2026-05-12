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
async def test_student_admin_suggestion_chat_flow(client: AsyncClient) -> None:
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-suggestion")
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-suggestion")

    student_headers = {"Authorization": f"Bearer {student_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    post_response = await client.post(
        "/api/v1/students/me/suggestions/messages",
        headers=student_headers,
        json={"message": "Please add more revision sessions for Chemistry."},
    )
    assert post_response.status_code == 200

    unread_response = await client.get(
        "/api/v1/admin/suggestions/unread-count",
        headers=admin_headers,
    )
    assert unread_response.status_code == 200
    assert unread_response.json()["unread_count"] >= 1

    threads_response = await client.get(
        "/api/v1/admin/suggestions/threads?limit=50&offset=0",
        headers=admin_headers,
    )
    assert threads_response.status_code == 200
    threads = threads_response.json()["items"]
    assert threads
    thread_id = threads[0]["id"]

    admin_messages_response = await client.get(
        f"/api/v1/admin/suggestions/threads/{thread_id}/messages?limit=100&offset=0",
        headers=admin_headers,
    )
    assert admin_messages_response.status_code == 200
    admin_messages = admin_messages_response.json()["items"]
    assert any("Chemistry" in item["message"] for item in admin_messages)

    unread_after_read = await client.get(
        "/api/v1/admin/suggestions/unread-count",
        headers=admin_headers,
    )
    assert unread_after_read.status_code == 200
    assert unread_after_read.json()["unread_count"] == 0

    reply_response = await client.post(
        f"/api/v1/admin/suggestions/threads/{thread_id}/messages",
        headers=admin_headers,
        json={"message": "Noted. We will publish an extra chemistry revision slot this week."},
    )
    assert reply_response.status_code == 200

    student_messages_response = await client.get(
        "/api/v1/students/me/suggestions/messages?limit=100&offset=0",
        headers=student_headers,
    )
    assert student_messages_response.status_code == 200
    student_messages = student_messages_response.json()["items"]
    assert any("extra chemistry revision" in item["message"] for item in student_messages)
