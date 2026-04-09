from datetime import datetime

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
async def test_student_registration_pending_then_approved_login(client: AsyncClient) -> None:
    suffix = str(int(datetime.now().timestamp()))
    phone = f"98989{suffix[-5:]}"

    register_response = await client.post(
        "/api/v1/auth/register/student",
        data={
            "name": "New Student",
            "class_name": "11",
            "stream": "science",
            "contact_number": phone,
            "password": "Student@123",
            "confirm_password": "Student@123",
            "parent_contact_number": "9000001234",
            "address": "Main Road, City",
            "school_details": "ABC School",
        },
    )
    assert register_response.status_code == 201
    request_id = register_response.json()["request_id"]

    login_pending = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": phone,
            "password": "Student@123",
            "device": {
                "device_id": "new-student-device",
                "platform": "android",
                "app_version": "1.0.0",
            },
        },
    )
    assert login_pending.status_code == 401
    assert "pending" in login_pending.json()["detail"].lower()

    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "admin-device-reg")
    headers = {"Authorization": f"Bearer {admin_token}"}

    inbox_response = await client.get(
        "/api/v1/admin/me/notifications?is_read=false&limit=20&offset=0",
        headers=headers,
    )
    assert inbox_response.status_code == 200
    inbox_items = inbox_response.json()["items"]
    assert any(
        item.get("metadata", {}).get("request_id") == request_id
        and item.get("title", "").lower().startswith("new student registration")
        for item in inbox_items
    )

    pending_response = await client.get(
        "/api/v1/admin/registration-requests?status=pending&role=all&limit=50&offset=0",
        headers=headers,
    )
    assert pending_response.status_code == 200
    pending_ids = {item["request_id"] for item in pending_response.json()["items"]}
    assert request_id in pending_ids

    approve_response = await client.post(
        f"/api/v1/admin/registration-requests/{request_id}/decision",
        headers=headers,
        json={"status": "approved", "note": "Verified documents"},
    )
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "approved"
    assert approve_response.json()["user_status"] == "active"

    login_approved = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": phone,
            "password": "Student@123",
            "device": {
                "device_id": "new-student-device-2",
                "platform": "android",
                "app_version": "1.0.0",
            },
        },
    )
    assert login_approved.status_code == 200
    roles = set(login_approved.json()["user"]["roles"])
    assert "student" in roles


@pytest.mark.anyio
async def test_teacher_registration_rejected_cannot_login(client: AsyncClient) -> None:
    suffix = str(int(datetime.now().timestamp()))
    phone = f"97979{suffix[-5:]}"

    register_response = await client.post(
        "/api/v1/auth/register/teacher",
        data={
            "name": "New Teacher",
            "age": "32",
            "gender": "male",
            "qualification": "MSc Mathematics",
            "specialization": "Algebra",
            "school_college": "City College",
            "contact_number": phone,
            "password": "Teacher@123",
            "confirm_password": "Teacher@123",
            "address": "Teacher Colony",
        },
    )
    assert register_response.status_code == 201
    request_id = register_response.json()["request_id"]

    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "admin-device-reg-2")
    headers = {"Authorization": f"Bearer {admin_token}"}

    reject_response = await client.post(
        f"/api/v1/admin/registration-requests/{request_id}/decision",
        headers=headers,
        json={"status": "rejected", "note": "Incomplete details"},
    )
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "rejected"

    login_rejected = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": phone,
            "password": "Teacher@123",
            "device": {
                "device_id": "new-teacher-device",
                "platform": "android",
                "app_version": "1.0.0",
            },
        },
    )
    assert login_rejected.status_code == 401
    assert "rejected" in login_rejected.json()["detail"].lower()
