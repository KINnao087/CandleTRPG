from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from backend.app.domain.action import PlayerAction
from backend.app.domain.api import (
    HostResolveRequest,
    HostRollBackRequest,
    JoinRequest,
    PlayerActionRequest,
    PlayerReadyRequest,
)
from backend.app.domain.context import Scene
from backend.app.domain.room import PlayerInfo
from backend.app.services.context_manager import ContextManager
from backend.app.services.turn_manager import TurnManager
from backend.app.storage.room_store import RoomRuntimeInfo, RoomStore

app = FastAPI(title="CandleTRPG-LAN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

room_store = RoomStore()


def build_initial_world() -> str:
    return (
        "这是一个近未来都市背景的局域网跑团。旧城区被企业、帮派和地下情报贩子共同控制。"
        "AI 主持人需要保持剧情集中在当前场景，只结算玩家本轮行动造成的直接结果。"
    )


def build_initial_scene() -> Scene:
    return Scene.from_dict({
        "time": "夜晚 21:30",
        "location": "MIX 酒馆",
        "description": (
            "酒馆里很安静，窗外的霓虹招牌时明时暗。吧台后方有一扇狭窄的后门，"
            "门后通向一条没有监控的暗巷。"
        ),
    })


def build_initial_characters() -> list[dict]:
    return [
        {
            "id": "char_001",
            "player_id": "player_001",
            "name": "林烛",
            "status": {
                "hp": 85,
                "conditions": [],
            },
            "inventory": ["终端", "短刀", "急救喷雾"],
        }
    ]


def get_or_create_room(room_id: str) -> RoomRuntimeInfo:
    room = room_store.get_room(room_id)
    if room is not None:
        return room

    context = ContextManager(
        world=build_initial_world(),
        scene=build_initial_scene(),
        characters=build_initial_characters(),
    )
    room = RoomRuntimeInfo(
        room_id=room_id,
        phase="planning",
        turn_manager=TurnManager(context),
    )
    room.timeline.append({
        "id": "event_001",
        "type": "scene",
        "title": "当前场景",
        "content": context.scene.get("description", ""),
        "timestamp": context.scene.get("time", ""),
    })
    room_store.add_room(room)
    return room


def parse_player_id(player_id: str) -> int:
    if player_id.startswith("player_"):
        return int(player_id.removeprefix("player_"))
    return int(player_id)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/rooms/{room_id}/state")
def get_room_state(room_id: str):
    return get_or_create_room(room_id).to_room_state()


@app.post("/api/rooms/{room_id}/join")
def join_room(room_id: str, payload: JoinRequest):
    room = get_or_create_room(room_id)
    player = room.add_player(
        PlayerInfo(
            id=0,
            name=payload.player_name,
            character_name=payload.character_name,
            is_host=payload.role == "host",
        )
    )

    return {
        "player_id": RoomRuntimeInfo._format_player_id(player.id),
        "room_state": room.to_room_state(),
    }


@app.post("/api/rooms/{room_id}/actions")
def player_action(room_id: str, payload: PlayerActionRequest):
    room = get_or_create_room(room_id)
    player_id = parse_player_id(payload.player_id)

    if player_id not in room.players:
        raise HTTPException(status_code=404, detail="player not found")

    action: PlayerAction = {
        "player_id": payload.player_id,
        "character_name": payload.character_name,
        "action_text": payload.action_text,
    }
    room.player_action(player_id, action)
    return room.to_room_state()


@app.post("/api/rooms/{room_id}/ready")
def player_ready(room_id: str, payload: PlayerReadyRequest):
    room = get_or_create_room(room_id)
    player_id = parse_player_id(payload.player_id)

    if player_id not in room.players:
        raise HTTPException(status_code=404, detail="player not found")

    room.change_player_status(player_id, payload.ready)
    return room.to_room_state()


@app.post("/api/host/resolve-turn")
def resolve_turn(payload: HostResolveRequest):
    room = get_or_create_room(payload.room_id)

    if payload.force:
        room.phase = "resolving"
        turn_index = room.turn_manager.turn_index
        result = room.turn_manager.resolve_turn(list(room.actions.values()))
        room.timeline.insert(0, {
            "id": f"event_{turn_index:03d}",
            "type": "turn_resolved",
            "title": f"第 {turn_index} 回合结算",
            "content": result.get("narration", ""),
            "timestamp": result.get("scene", {}).get("time", ""),
        })
        room.actions.clear()
        for player_id in room.player_status:
            room.player_status[player_id] = False
        room.phase = "planning"
    else:
        resolved = room.try_resolve_turn()
        if not resolved:
            raise HTTPException(status_code=409, detail="not all players are ready")

    return room.to_room_state()


@app.post("/api/host/rollback")
def rollback(payload: HostRollBackRequest):
    room = get_or_create_room(payload.room_id)
    room.phase = "planning"
    return room.to_room_state()
