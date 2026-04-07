import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_student_notices_list(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "student@test.local",
            "password": "Student@123",
            "device": {"device_id": "test-device-2", "platform": "android", "app_version": "1.0.0"},
        },
    )
    assert login.status_code == 200
    token = login.json()["tokens"]["access_token"]

    response = await client.get(
        "/api/v1/students/me/notices",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert len(body["items"]) >= 1
