from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.realtime.notification_hub import notification_hub
from app.repositories.notification_repo import NotificationRepository
from app.repositories.user_repo import UserRepository

router = APIRouter(tags=["ws-notifications"])
settings = get_settings()


def _extract_access_token(websocket: WebSocket) -> str | None:
    token = websocket.query_params.get("token")
    if token:
        return token
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    cookie_token = websocket.cookies.get(settings.access_token_cookie_name)
    if cookie_token and cookie_token.strip():
        if cookie_token.lower().startswith("bearer "):
            return cookie_token[7:].strip()
        return cookie_token.strip()
    return None


@router.websocket("/ws/notifications")
async def notifications_socket(websocket: WebSocket) -> None:
    token = _extract_access_token(websocket)
    if not token:
        await websocket.close(code=4401, reason="Missing access token")
        return

    user_id: str | None = None
    unread_count = 0
    async with AsyncSessionLocal() as session:
        from app.core.security import decode_token

        try:
            payload = decode_token(token)
        except ValueError:
            await websocket.close(code=4401, reason="Invalid access token")
            return

        if payload.get("typ") != "access":
            await websocket.close(code=4401, reason="Invalid token type")
            return

        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4401, reason="Invalid token payload")
            return

        user = await UserRepository(session).get_by_id(user_id)
        if not user:
            await websocket.close(code=4401, reason="User not found")
            return

        user_status = user.status.value if hasattr(user.status, "value") else str(user.status)
        if user_status != "active":
            await websocket.close(code=4401, reason="User is inactive")
            return

        user_id = user.id
        unread_count = await NotificationRepository(session).unread_count(user_id=user_id)

    if not user_id:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await notification_hub.connect(user_id=user_id, websocket=websocket)
    try:
        await websocket.send_json({"event": "notification.unread_count", "unread_count": unread_count})

        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_json({"event": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        await notification_hub.disconnect(user_id=user_id, websocket=websocket)
