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
            "targets": [{"target_type": "all", "target_id": "all"}],
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
async def test_admin_can_manage_parent_links_and_fee_reconciliation(client: AsyncClient) -> None:
    admin_token = await _login_token(client, "admin@test.local", "Admin@123", "device-admin-4")
    headers = {"Authorization": f"Bearer {admin_token}"}

    parents_response = await client.get("/api/v1/admin/parents?limit=20&offset=0", headers=headers)
    assert parents_response.status_code == 200
    parents = parents_response.json()["items"]
    assert len(parents) >= 1

    parent_user_id = parents[0]["user_id"]
    parent_id = parents[0]["parent_id"]

    students_response = await client.get("/api/v1/admin/students?limit=20&offset=0", headers=headers)
    assert students_response.status_code == 200
    existing_student = students_response.json()["items"][0]
    batch_id = existing_student["batch"]["id"]

    unique_suffix = int(datetime.now(UTC).timestamp())
    create_student_response = await client.post(
        "/api/v1/admin/students",
        headers=headers,
        json={
            "full_name": "Linked Student",
            "email": f"linked-{unique_suffix}@example.com",
            "phone": "9000099999",
            "password": "Student@123",
            "admission_no": f"ADM-LINK-{unique_suffix}",
            "roll_no": f"R-{unique_suffix}",
            "batch_id": batch_id,
        },
    )
    assert create_student_response.status_code == 200
    new_student_id = create_student_response.json()["student_id"]

    create_link_response = await client.post(
        "/api/v1/admin/parents/links",
        headers=headers,
        json={
            "parent_user_id": parent_user_id,
            "student_id": new_student_id,
            "relation_type": "guardian",
            "is_primary": False,
        },
    )
    assert create_link_response.status_code == 200
    assert create_link_response.json()["student_id"] == new_student_id

    links_response = await client.get(
        f"/api/v1/admin/parents/{parent_id}/links?limit=20&offset=0",
        headers=headers,
    )
    assert links_response.status_code == 200
    linked_student_ids = {item["student_id"] for item in links_response.json()["items"]}
    assert new_student_id in linked_student_ids

    invoice_no = f"INV-ADM-{unique_suffix}"
    create_invoice_response = await client.post(
        "/api/v1/admin/fee-invoices",
        headers=headers,
        json={
            "student_id": new_student_id,
            "invoice_no": invoice_no,
            "period_label": "Apr-2026",
            "due_date": (date.today() + timedelta(days=30)).isoformat(),
            "amount": 3500,
            "status": "pending",
        },
    )
    assert create_invoice_response.status_code == 200
    invoice_id = create_invoice_response.json()["id"]

    list_invoices_response = await client.get(
        f"/api/v1/admin/fee-invoices?student_id={new_student_id}&limit=20&offset=0",
        headers=headers,
    )
    assert list_invoices_response.status_code == 200
    invoice_ids = {item["id"] for item in list_invoices_response.json()["items"]}
    assert invoice_id in invoice_ids

    payments_response = await client.get("/api/v1/admin/payments?limit=20&offset=0", headers=headers)
    assert payments_response.status_code == 200
    payments = payments_response.json()["items"]
    assert len(payments) >= 1

    payment_id = payments[0]["id"]
    reconcile_response = await client.patch(
        f"/api/v1/admin/payments/{payment_id}/reconcile",
        headers=headers,
        json={
            "status": "refunded",
            "note": "Manual reconciliation during phase 4 rollout.",
        },
    )
    assert reconcile_response.status_code == 200
    reconciled = reconcile_response.json()
    assert reconciled["status"] == "refunded"
    assert reconciled["invoice_status"] == "pending"
