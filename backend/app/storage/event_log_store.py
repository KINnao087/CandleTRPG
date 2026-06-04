import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class EventLogStore:
    def __init__(self, base_dir: str | Path = "backend/saves"):
        self.base_dir = Path(base_dir)

    def append(
        self,
        room_hash: str,
        room_id: str,
        event_type: str,
        payload: dict,
        turn_index: int | None = None,
    ) -> dict:
        event = {
            "event_id": f"evt_{uuid4().hex}",
            "room_id": room_id,
            "room_hash": room_hash,
            "turn_index": turn_index,
            "type": event_type,
            "payload": payload,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        log_path = self._log_path(room_hash)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False))
            file.write("\n")

        return event

    def _log_path(self, room_hash: str) -> Path:
        return self.base_dir / room_hash / "event_log.jsonl"
