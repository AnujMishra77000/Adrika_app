from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

from app.services.assessment_service import AssessmentService


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


async def _math_subject_id(client: AsyncClient, admin_token: str) -> str:
    response = await client.get(
        "/api/v1/admin/subjects?limit=100&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    for item in response.json()["items"]:
        if item["code"] == "MATH":
            return item["id"]
    raise AssertionError("MATH subject not found in seeded dataset")


async def _create_question(
    client: AsyncClient,
    admin_token: str,
    *,
    subject_id: str,
    topic: str,
    prompt: str,
) -> str:
    response = await client.post(
        "/api/v1/admin/assessments/question-bank",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "class_level": 10,
            "subject_id": subject_id,
            "topic": topic,
            "prompt": prompt,
            "options": [
                {"key": "A", "text": "4"},
                {"key": "B", "text": "5"},
                {"key": "C", "text": "6"},
                {"key": "D", "text": "7"},
            ],
            "correct_option_key": "A",
            "difficulty": "easy",
            "default_marks": 2,
            "is_active": True,
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


async def _create_test(
    client: AsyncClient,
    admin_token: str,
    *,
    subject_id: str,
    question_id: str,
    title: str,
) -> str:
    response = await client.post(
        "/api/v1/admin/assessments/create-test",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": title,
            "description": "Chapter practice test",
            "class_level": 10,
            "subject_id": subject_id,
            "topic": "Algebra",
            "assessment_type": "scheduled",
            "duration_minutes": 30,
            "attempt_limit": 1,
            "passing_marks": 1,
            "questions": [
                {
                    "question_id": question_id,
                    "marks": 2,
                    "negative_marks": 0,
                }
            ],
        },
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.mark.anyio
async def test_admin_can_build_assign_and_student_can_attempt_test(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-assessment-1")
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-assessment-1")

    subject_id = await _math_subject_id(client, admin_token)
    question_id = await _create_question(
        client,
        admin_token,
        subject_id=subject_id,
        topic="Algebra Basics",
        prompt="What is 2 + 2?",
    )

    assessment_id = await _create_test(
        client,
        admin_token,
        subject_id=subject_id,
        question_id=question_id,
        title="Scheduled Math Test - Flow 1",
    )

    now = datetime.now(UTC)
    assign_response = await client.post(
        f"/api/v1/admin/assessments/{assessment_id}/assign",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "starts_at": (now - timedelta(minutes=5)).isoformat(),
            "ends_at": (now + timedelta(minutes=55)).isoformat(),
            "targets": [{"target_type": "all_students", "target_id": "all"}],
            "publish": True,
            "send_notification": True,
        },
    )
    assert assign_response.status_code == 200
    assert assign_response.json()["assigned_students"] >= 1

    list_response = await client.get(
        "/api/v1/students/me/tests?limit=50&offset=0",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    test_item = next((item for item in items if item["id"] == assessment_id), None)
    assert test_item is not None
    assert test_item["availability"] in {"live", "scheduled"}

    start_response = await client.post(
        f"/api/v1/students/me/tests/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    attempt_id = start_payload["attempt_id"]
    question_to_answer = start_payload["questions"][0]["question_id"]

    save_response = await client.put(
        f"/api/v1/students/me/tests/attempts/{attempt_id}/answers/{question_to_answer}",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"selected_key": "A"},
    )
    assert save_response.status_code == 200

    submit_response = await client.post(
        f"/api/v1/students/me/tests/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert submit_response.status_code == 200
    submit_payload = submit_response.json()
    assert submit_payload["status"] == "submitted"
    assert submit_payload["score"] == pytest.approx(2.0)
    assert submit_payload["is_passed"] is True
    assert submit_payload["question_evaluation"][0]["is_correct"] is True

    notifications_response = await client.get(
        "/api/v1/students/me/notifications?limit=20&offset=0",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert notifications_response.status_code == 200
    assert any(
        item["notification_type"] == "test" and item.get("metadata", {}).get("assessment_id") == assessment_id
        for item in notifications_response.json()["items"]
    )


@pytest.mark.anyio
async def test_scheduler_marks_absent_for_missed_assessment(client: AsyncClient, db_session) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-assessment-2")
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-assessment-2")

    subject_id = await _math_subject_id(client, admin_token)
    question_id = await _create_question(
        client,
        admin_token,
        subject_id=subject_id,
        topic="Arithmetic",
        prompt="What is 3 + 1?",
    )

    assessment_id = await _create_test(
        client,
        admin_token,
        subject_id=subject_id,
        question_id=question_id,
        title="Scheduled Math Test - Missed",
    )

    now = datetime.now(UTC)
    assign_response = await client.post(
        f"/api/v1/admin/assessments/{assessment_id}/assign",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "starts_at": (now - timedelta(hours=2)).isoformat(),
            "ends_at": (now - timedelta(hours=1)).isoformat(),
            "targets": [{"target_type": "all_students", "target_id": "all"}],
            "publish": True,
            "send_notification": False,
        },
    )
    assert assign_response.status_code == 200

    stats = await AssessmentService(db_session).process_scheduled_events()
    assert stats["ended_assessments_scanned"] >= 1

    results_response = await client.get(
        "/api/v1/students/me/results?limit=100&offset=0",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert results_response.status_code == 200
    items = results_response.json()["items"]
    result_row = next((item for item in items if item["assessment_id"] == assessment_id), None)
    assert result_row is not None
    assert float(result_row["score"]) == pytest.approx(0.0)


@pytest.mark.anyio
async def test_admin_can_delete_unused_question_and_block_delete_if_question_is_used(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-assessment-delete")

    subject_id = await _math_subject_id(client, admin_token)

    unused_question_id = await _create_question(
        client,
        admin_token,
        subject_id=subject_id,
        topic="Delete Topic",
        prompt="Delete me?",
    )

    delete_unused_response = await client.delete(
        f"/api/v1/admin/assessments/question-bank/{unused_question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_unused_response.status_code == 200
    assert delete_unused_response.json()["deleted"] is True

    used_question_id = await _create_question(
        client,
        admin_token,
        subject_id=subject_id,
        topic="Used Topic",
        prompt="Should not delete once linked",
    )

    _ = await _create_test(
        client,
        admin_token,
        subject_id=subject_id,
        question_id=used_question_id,
        title="Question Link Test",
    )

    delete_used_response = await client.delete(
        f"/api/v1/admin/assessments/question-bank/{used_question_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert delete_used_response.status_code == 409
    assert "Deactivate" in delete_used_response.json().get("detail", "")


@pytest.mark.anyio
async def test_admin_result_topic_views_and_whatsapp_send(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-assessment-result-1")
    student_token = await _login_token(client, "student@test.local", "Student@123", "device-student-assessment-result-1")

    subject_id = await _math_subject_id(client, admin_token)
    question_id = await _create_question(
        client,
        admin_token,
        subject_id=subject_id,
        topic="Result Topic",
        prompt="Result verification question",
    )
    assessment_id = await _create_test(
        client,
        admin_token,
        subject_id=subject_id,
        question_id=question_id,
        title="Result Topic Test",
    )

    now = datetime.now(UTC)
    assign_response = await client.post(
        f"/api/v1/admin/assessments/{assessment_id}/assign",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "starts_at": (now - timedelta(minutes=10)).isoformat(),
            "ends_at": (now + timedelta(minutes=50)).isoformat(),
            "targets": [{"target_type": "all_students", "target_id": "all"}],
            "publish": True,
            "send_notification": False,
        },
    )
    assert assign_response.status_code == 200

    start_response = await client.post(
        f"/api/v1/students/me/tests/{assessment_id}/attempts",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert start_response.status_code == 200
    attempt_id = start_response.json()["attempt_id"]
    question_to_answer = start_response.json()["questions"][0]["question_id"]

    save_response = await client.put(
        f"/api/v1/students/me/tests/attempts/{attempt_id}/answers/{question_to_answer}",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"selected_key": "A"},
    )
    assert save_response.status_code == 200

    submit_response = await client.post(
        f"/api/v1/students/me/tests/attempts/{attempt_id}/submit",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert submit_response.status_code == 200

    topics_response = await client.get(
        "/api/v1/admin/results/topics?class_level=10&limit=50&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert topics_response.status_code == 200
    topic_items = topics_response.json()["items"]
    current_topic = next((item for item in topic_items if item["assessment_id"] == assessment_id), None)
    assert current_topic is not None

    students_response = await client.get(
        f"/api/v1/admin/results/topics/{assessment_id}/students?limit=50&offset=0",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert students_response.status_code == 200
    student_items = students_response.json()["items"]
    assert len(student_items) >= 1
    assert student_items[0]["rank"] >= 1

    target_student_id = student_items[0]["student"]["id"]
    wa_response = await client.post(
        f"/api/v1/admin/results/topics/{assessment_id}/students/{target_student_id}/whatsapp",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"phone": "9876543210"},
    )
    assert wa_response.status_code == 200
    assert wa_response.json()["delivery_status"] in {"sent", "mock_sent", "failed"}
