import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_student_content_returns_banner_and_daily_thought(client: AsyncClient) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "student@test.local",
            "password": "Student@123",
            "device": {"device_id": "test-device-content", "platform": "android", "app_version": "1.0.0"},
        },
    )
    assert login.status_code == 200
    token = login.json()["tokens"]["access_token"]

    response = await client.get(
        "/api/v1/students/me/content",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["daily_thought"] is not None
    assert body["daily_thought"]["text"]
    assert len(body["banners"]) >= 1
    assert body["banners"][0]["title"] == "Welcome Banner"
