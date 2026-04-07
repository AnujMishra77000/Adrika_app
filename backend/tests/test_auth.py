import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_login_success(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "identifier": "student@test.local",
            "password": "Student@123",
            "device": {"device_id": "test-device-1", "platform": "android", "app_version": "1.0.0"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "tokens" in body
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]
