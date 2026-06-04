from backend.app.domain.room import Room
from typing import Any
import json

from backend.app.utils.crypto import hmac_sha256_base64url
from backend.app.utils.json_parse import normalize_to_json, stable_json_dumps

ROOM_HASH_VERSION = "room_hash_v1"
ROOM_HASH_LENGTH = 20

def build_room_hash_payload(room: Room) -> dict[str, Any]:
    return {
        "version": ROOM_HASH_VERSION,
        "room_id": room.room_id,
        "world": {
            "title": room.world.title,
            "setting": room.world.setting,
        },
        "opening_scene": room.opening_scene,
        "created_at": room.created_at,
    }

def calc_room_hash(room: Room, secret: str) -> str:
    payload = build_room_hash_payload(room)
    raw = stable_json_dumps(payload)

    return hmac_sha256_base64url(
        text=raw,
        secret=secret,
        length_bytes=ROOM_HASH_LENGTH,
    )
