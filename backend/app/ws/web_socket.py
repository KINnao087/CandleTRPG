from fastapi import WebSocket
from collections import defaultdict

class RoomConnectionManager:
    connections: dict[str, list[WebSocket]]
    def __init__(self) -> None:
        self.connections = defaultdict(list)

    async def connect(self, room_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.connections[room_id].append(ws)

    def disconnect(self, room_id: str, ws: WebSocket) -> None:
        if room_id not in self.connections:
            return
        if ws in self.connections[room_id]:
            self.connections[room_id].remove(ws)
        if not self.connections[room_id]:
            del self.connections[room_id]

    async def broadcast_room_state(self, room_id: str, room_state: dict) -> None:
        message = {
            "type" : "room_state",
            "room_id": room_id,
            "payload": room_state,
        }
        for ws in list(self.connections.get(room_id, [])):
            await ws.send_json(message)
