import json
from datetime import datetime, timezone
from pathlib import Path

from backend.app.storage.room_store import RoomRuntimeInfo


class SnapshotStore:
    def __init__(self, base_dir: str | Path = "backend/saves"):
        self.base_dir = Path(base_dir)

    def save_snapshot(self, room: RoomRuntimeInfo) -> Path:
        turn_index = self._snapshot_turn_index(room)
        path = self._snapshot_path(room.room.room_hash, turn_index)
        self._write_snapshot(path, room.to_snapshot())
        return path

    def save_latest(self, room: RoomRuntimeInfo) -> Path:
        path = self._latest_path(room.room.room_hash)
        self._write_snapshot(path, room.to_snapshot())
        return path

    def load_latest(self, room_hash: str) -> RoomRuntimeInfo | None:
        room_dir = self._find_room_dir(room_hash)
        if room_dir is None:
            return None
        return self._load_snapshot(room_dir / "snapshots" / "latest.json")

    def load_turn(self, room_hash: str, turn_index: int) -> RoomRuntimeInfo | None:
        room_dir = self._find_room_dir(room_hash)
        if room_dir is None:
            return None
        return self._load_snapshot(room_dir / "snapshots" / f"turn_{turn_index:03d}.json")

    def list_snapshots(self, room_hash: str) -> list[int]:
        room_dir = self._find_room_dir(room_hash)
        if room_dir is None:
            return []

        snapshots_dir = room_dir / "snapshots"
        if not snapshots_dir.exists():
            return []

        turn_indexes: list[int] = []
        for path in snapshots_dir.glob("turn_*.json"):
            try:
                turn_indexes.append(int(path.stem.removeprefix("turn_")))
            except ValueError:
                continue

        return sorted(turn_indexes)

    def list_rooms(self):
        rooms = []

        if not self.base_dir.exists():
            return rooms

        for room_dir in self.base_dir.iterdir():
            if not room_dir.is_dir():
                continue

            latest_path = room_dir / "snapshots" / "latest.json"
            if not latest_path.exists():
                continue

            try:
                data = json.loads(latest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            if not isinstance(data, dict):
                continue

            players = data.get("players", [])
            if not isinstance(players, list):
                players = []

            online_players = [
                player for player in players
                if isinstance(player, dict) and player.get("is_online") is True
            ]

            world = data.get("world", {})
            if not isinstance(world, dict):
                world = {}

            room_id = str(data.get("room_id", room_dir.name))
            rooms.append({
                "room_id": room_id,
                "room_hash": str(data.get("room_hash") or RoomRuntimeInfo.build_room_hash(room_id)),
                "title": str(world.get("title", "")),
                "phase": str(data.get("phase", "planning")),
                "turn_index": int(data.get("turn_index", 1)),
                "player_count": len(players),
                "online_player_count": len(online_players),
                "host_player_id": str(data.get("host_player_id") or ""),
                "created_at": str(data.get("created_at") or ""),
                "updated_at": str(data.get("updated_at") or datetime.fromtimestamp(
                    latest_path.stat().st_mtime,
                    timezone.utc,
                ).isoformat()),
            })

        return rooms

    def has_room_hash(self, room_hash: str) -> bool:
        return self._find_room_dir(room_hash) is not None

    def _write_snapshot(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_snapshot(self, path: Path) -> RoomRuntimeInfo | None:
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None

        return RoomRuntimeInfo.from_snapshot(data)

    def _snapshot_turn_index(self, room: RoomRuntimeInfo) -> int:
        return max(0, room.turn_manager.turn_index - 1)

    def _find_room_dir(self, room_hash: str) -> Path | None:
        direct_dir = self._room_dir(room_hash)
        if (direct_dir / "snapshots" / "latest.json").exists():
            return direct_dir

        if not self.base_dir.exists():
            return None

        for room_dir in self.base_dir.iterdir():
            if not room_dir.is_dir():
                continue

            latest_path = room_dir / "snapshots" / "latest.json"
            if not latest_path.exists():
                continue

            try:
                data = json.loads(latest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue

            if not isinstance(data, dict):
                continue

            stored_room_id = str(data.get("room_id", room_dir.name))
            stored_room_hash = str(data.get("room_hash") or RoomRuntimeInfo.build_room_hash(stored_room_id))
            if stored_room_hash == room_hash:
                return room_dir

        return None

    def _room_dir(self, room_hash: str) -> Path:
        return self.base_dir / room_hash

    def _snapshots_dir(self, room_hash: str) -> Path:
        return self._room_dir(room_hash) / "snapshots"

    def _snapshot_path(self, room_hash: str, turn_index: int) -> Path:
        return self._snapshots_dir(room_hash) / f"turn_{turn_index:03d}.json"

    def _latest_path(self, room_hash: str) -> Path:
        return self._snapshots_dir(room_hash) / "latest.json"
