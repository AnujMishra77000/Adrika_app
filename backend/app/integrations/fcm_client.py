from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class FCMDeliveryResult:
    success: bool
    status: str
    provider_message_id: str | None = None
    provider_response: str | None = None
    invalid_token: bool = False
    retryable: bool = False


class FCMClient:
    """FCM HTTP v1 sender with graceful local-dev fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def _load_credentials_info(self) -> dict[str, Any] | None:
        path_override = (self.settings.fcm_credentials_path or "").strip()
        if path_override:
            path = Path(path_override).expanduser()
            if not path.exists():
                logger.warning("fcm_credentials_path_missing", path=str(path))
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        raw = (self.settings.fcm_credentials_json or "").strip()
        if not raw:
            return None
        if raw.startswith("{"):
            return json.loads(raw)

        path = Path(raw).expanduser()
        if not path.exists():
            logger.warning("fcm_credentials_json_path_missing", path=str(path))
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _build_access_token(self) -> str | None:
        info = self._load_credentials_info()
        if not info:
            return None

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.service_account import Credentials
        except Exception as exc:  # pragma: no cover - runtime-only branch
            logger.warning("fcm_google_auth_missing", reason=str(exc))
            return None

        credentials = Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(Request())
        return credentials.token

    async def send(
        self,
        *,
        device_token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> FCMDeliveryResult:
        if not self.settings.fcm_project_id:
            return FCMDeliveryResult(
                success=False,
                status="skipped",
                provider_response="fcm_project_id_not_configured",
                retryable=False,
            )

        access_token = self._build_access_token()
        if not access_token:
            return FCMDeliveryResult(
                success=False,
                status="skipped",
                provider_response="fcm_credentials_not_configured",
                retryable=False,
            )

        payload = {
            "message": {
                "token": device_token,
                "notification": {"title": title, "body": body},
                "data": data or {},
                "android": {
                    "priority": "high",
                    "notification": {
                        "channel_id": "adr_notifications_high",
                        "sound": "default",
                    },
                },
                "apns": {
                    "headers": {"apns-priority": "10"},
                    "payload": {"aps": {"sound": "default"}},
                },
            }
        }

        url = f"https://fcm.googleapis.com/v1/projects/{self.settings.fcm_project_id}/messages:send"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            return FCMDeliveryResult(
                success=False,
                status="failed",
                provider_response=str(exc),
                retryable=True,
            )

        body_text = response.text
        if response.status_code == 200:
            provider_message_id = response.json().get("name")
            return FCMDeliveryResult(
                success=True,
                status="sent",
                provider_message_id=provider_message_id,
                provider_response=body_text,
                retryable=False,
            )

        upper = body_text.upper()
        invalid = "UNREGISTERED" in upper or "INVALID_ARGUMENT" in upper
        retryable = response.status_code >= 500 or response.status_code in {408, 429}
        status = "invalid_token" if invalid else "failed"
        return FCMDeliveryResult(
            success=False,
            status=status,
            provider_response=body_text,
            invalid_token=invalid,
            retryable=retryable and not invalid,
        )
