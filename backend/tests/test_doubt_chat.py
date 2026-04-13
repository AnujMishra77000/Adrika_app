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
async def test_lecture_based_doubt_chat_flow(client: AsyncClient) -> None:
    teacher_token = await _login_token(client, "teacher@test.local", "Teacher@123", "device-teacher-doubt-chat")
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-doubt-chat")
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-doubt-chat")

    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    student_headers = {"Authorization": f"Bearer {student_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    assignments_response = await client.get("/api/v1/teachers/me/assignments", headers=teacher_headers)
    assert assignments_response.status_code == 200
    assignments = assignments_response.json()["items"]
    assert assignments
    assignment = assignments[0]

    create_lecture_response = await client.post(
        "/api/v1/teachers/me/lectures/done",
        headers=teacher_headers,
        json={
            "subject_id": assignment["subject_id"],
            "topic": "Quadratic equations revision",
            "summary": "Revision of factorization and roots methods.",
            "class_level": 10,
            "batch_id": assignment["batch_id"],
        },
    )
    assert create_lecture_response.status_code == 200
    lecture_id = create_lecture_response.json()["lecture_id"]

    list_lectures_response = await client.get(
        "/api/v1/students/me/doubts/lectures/done?limit=20&offset=0",
        headers=student_headers,
    )
    assert list_lectures_response.status_code == 200
    lecture_items = list_lectures_response.json()["items"]
    assert any(item["lecture_id"] == lecture_id for item in lecture_items)

    raise_doubt_response = await client.post(
        f"/api/v1/students/me/doubts/lectures/done/{lecture_id}/raise",
        headers=student_headers,
        json={
            "topic": "Need help with discriminant",
            "description": "How to identify roots quickly from discriminant value?",
        },
    )
    assert raise_doubt_response.status_code == 200
    doubt_id = raise_doubt_response.json()["id"]

    teacher_doubts_response = await client.get("/api/v1/teachers/me/doubts?limit=50&offset=0", headers=teacher_headers)
    assert teacher_doubts_response.status_code == 200
    teacher_doubts = teacher_doubts_response.json()["items"]
    assert any(item["id"] == doubt_id for item in teacher_doubts)

    teacher_reply_response = await client.post(
        f"/api/v1/teachers/me/doubts/{doubt_id}/messages",
        headers=teacher_headers,
        json={"message": "Check b²-4ac first. If positive, roots are real and distinct."},
    )
    assert teacher_reply_response.status_code == 200

    student_messages_response = await client.get(
        f"/api/v1/students/me/doubts/{doubt_id}/messages",
        headers=student_headers,
    )
    assert student_messages_response.status_code == 200
    student_messages = student_messages_response.json()["items"]
    assert len(student_messages) >= 1
    assert any("b²-4ac" in message["message"] for message in student_messages)

    admin_conversation_response = await client.get(
        f"/api/v1/admin/doubts/{doubt_id}/conversation",
        headers=admin_headers,
    )
    assert admin_conversation_response.status_code == 200
    conversation = admin_conversation_response.json()
    assert conversation["doubt"]["id"] == doubt_id
    assert len(conversation["messages"]) >= 1
