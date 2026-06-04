from fastapi import WebSocket
from collections import defaultdict

class RoomConnectionManager:
    connections: dict[str, list[WebSocket]]
    def __init__(self) -> None:
        self.connections = defaultdict(list)

    async def connect(self, room_hash: str, ws: WebSocket) -> None:
        await ws.accept()
        self.connections[room_hash].append(ws)

    def disconnect(self, room_hash: str, ws: WebSocket) -> None:
        if room_hash not in self.connections:
            return
        if ws in self.connections[room_hash]:
            self.connections[room_hash].remove(ws)
        if not self.connections[room_hash]:
            del self.connections[room_hash]

    async def broadcast_room_state(self, room_hash: str, room_state: dict) -> None:
        message = {
            "type" : "room_state",
            "room_id": room_state.get("room_id", ""),
            "room_hash": room_hash,
            "payload": room_state,
        }
        for ws in list(self.connections.get(room_hash, [])):
            await ws.send_json(message)
