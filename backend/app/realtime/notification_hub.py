from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket


class NotificationHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, *, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)

    async def disconnect(self, *, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            if user_id not in self._connections:
                return
            self._connections[user_id].discard(websocket)
            if not self._connections[user_id]:
                self._connections.pop(user_id, None)

    def is_online(self, *, user_id: str) -> bool:
        sockets = self._connections.get(user_id)
        return bool(sockets)

    async def send_to_user(self, *, user_id: str, payload: dict) -> None:
        async with self._lock:
            sockets = list(self._connections.get(user_id, set()))

        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(payload)
            except Exception:
                stale.append(socket)

        if not stale:
            return

        async with self._lock:
            active = self._connections.get(user_id)
            if not active:
                return
            for socket in stale:
                active.discard(socket)
            if not active:
                self._connections.pop(user_id, None)


notification_hub = NotificationHub()

