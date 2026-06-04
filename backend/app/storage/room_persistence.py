from pathlib import Path
from typing import Any

from backend.app.storage.event_log_store import EventLogStore
from backend.app.storage.room_store import RoomRuntimeInfo
from backend.app.storage.snapshot_store import SnapshotStore


class RoomPersistence:
    def __init__(self, base_dir: str | Path = "backend/saves"):
        self.event_log_store = EventLogStore(base_dir)
        self.snapshot_store = SnapshotStore(base_dir)

    def append_event(
        self,
        room: RoomRuntimeInfo,
        event_type: str,
        payload: dict[str, Any],
    ) -> dict:
        return self.event_log_store.append(
            room_hash=room.room.room_hash,
            room_id=room.room_id,
            event_type=event_type,
            payload=payload,
            turn_index=self._event_turn_index(room, event_type),
        )

    def save_room(self, room: RoomRuntimeInfo) -> None:
        self.snapshot_store.save_latest(room)

    def save_initial_room(self, room: RoomRuntimeInfo) -> None:
        self.snapshot_store.save_snapshot(room)
        self.snapshot_store.save_latest(room)

    def save_turn_snapshot(self, room: RoomRuntimeInfo) -> None:
        self.snapshot_store.save_snapshot(room)
        self.snapshot_store.save_latest(room)

    def load_latest_room(self, room_hash: str) -> RoomRuntimeInfo | None:
        return self.snapshot_store.load_latest(room_hash)

    def rollback_room(self, room_hash: str, turn_index: int) -> RoomRuntimeInfo | None:
        return self.snapshot_store.load_turn(room_hash, turn_index)

    def list_saved_rooms(self) -> list[dict]:
        return self.snapshot_store.list_rooms()

    def has_room_hash(self, room_hash: str) -> bool:
        return self.snapshot_store.has_room_hash(room_hash)

    def _event_turn_index(self, room: RoomRuntimeInfo, event_type: str) -> int:
        if event_type == "room_created":
            return 0

        if event_type in {"turn_resolved", "rollback"}:
            return max(0, room.turn_manager.turn_index - 1)

        return room.turn_manager.turn_index
