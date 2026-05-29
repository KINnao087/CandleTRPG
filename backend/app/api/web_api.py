from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from backend.app.domain.action import PlayerAction
from backend.app.domain.api import (
    HostResolveRequest,
    HostRollBackRequest,
    JoinRequest,
    PlayerActionRequest,
    PlayerReadyRequest,
    CreateRoomRequest,
    WorldRequest,
)
from backend.app.domain.context import Scene, World
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


# def build_initial_world() -> str:
#     return (
#         "这是一个近未来都市背景的局域网跑团。旧城区被企业、帮派和地下情报贩子共同控制。"
#         "AI 主持人需要保持剧情集中在当前场景，只结算玩家本轮行动造成的直接结果。"
#     )
#
#
# def build_initial_scene() -> Scene:
#     return Scene.from_dict({
#         "time": "夜晚 21:30",
#         "location": "MIX 酒馆",
#         "description": (
#             "酒馆里很安静，窗外的霓虹招牌时明时暗。吧台后方有一扇狭窄的后门，"
#             "门后通向一条没有监控的暗巷。"
#         ),
#     })
#
#
# def build_initial_characters() -> list[dict]:
#     return [
#         {
#             "id": "char_001",
#             "player_id": "player_001",
#             "name": "林烛",
#             "status": {
#                 "hp": 85,
#                 "conditions": [],
#             },
#             "inventory": ["终端", "短刀", "急救喷雾"],
#         }
#     ]


def _get_room(room_id: str) -> RoomRuntimeInfo | None:
    return room_store.get_room(room_id)


def _create_room(room_id: str, payload: CreateRoomRequest) -> RoomRuntimeInfo:
    world = World(title=payload.world.title, setting=payload.world.setting)
    scene = Scene.from_dict({
        "time": "",
        "location": "",
        "description": payload.world.opening_scene,
    })
    host = PlayerInfo(
        id=0,
        name=payload.host_name,
        character_name=payload.character_name,
        is_host=True,
    )

    room_runtime_info = RoomRuntimeInfo(
        room_id=room_id,
        phase="planning",
        turn_manager=TurnManager(ContextManager(
            world=world,
            characters=[host],
            scene=scene
        )),
        world=world
    )
    room_runtime_info.add_player(host)
    room_runtime_info.timeline.append({
        "id": "event_001",
        "type": "scene",
        "title": "当前场景",
        "content": payload.world.opening_scene,
        "timestamp": scene.get("time", ""),
    })

    return room_runtime_info


def _update_room_world(room: RoomRuntimeInfo, payload: WorldRequest) -> None:
    room.world = World(title=payload.title, setting=payload.setting)
    context = room.turn_manager.context_manager
    context.world = room.world
    context.scene = Scene.from_dict({
        "time": context.scene.get("time", ""),
        "location": context.scene.get("location", ""),
        "description": payload.opening_scene,
    })

    if room.timeline:
        room.timeline[-1]["content"] = payload.opening_scene
    else:
        room.timeline.append({
            "id": "event_001",
            "type": "scene",
            "title": "当前场景",
            "content": payload.opening_scene,
            "timestamp": context.scene.get("time", ""),
        })

def parse_player_id(player_id: str) -> int:
    if player_id.startswith("player_"):
        return int(player_id.removeprefix("player_"))
    return int(player_id)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/rooms/{room_id}")
def create_room(room_id: str, payload: CreateRoomRequest):
    room = _get_room(room_id)
    if room is None:
        room = _create_room(room_id, payload)
        room_store.add_room(room)

    host = next(player for player in room.players.values() if player.is_host)
    return {
        "player_id": RoomRuntimeInfo._format_player_id(host.id),
        "room_state": room.to_room_state(),
    }


@app.post("/api/rooms/{room_id}/world")
def import_world(room_id: str, payload: WorldRequest):
    room = _get_room(room_id)
    if room is None:
        return None

    _update_room_world(room, payload)
    return {
        "room_state": room.to_room_state(),
    }


@app.get("/api/rooms/{room_id}/state")
def get_room_state(room_id: str):
    room = _get_room(room_id)
    if room is None:
        return None
    return room.to_room_state()


@app.post("/api/rooms/{room_id}/join")
def join_room(room_id: str, payload: JoinRequest):
    room = _get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    if payload.role == "host":
        for current_player in room.players.values():
            if current_player.is_host:
                return {
                    "player_id": RoomRuntimeInfo._format_player_id(current_player.id),
                    "room_state": room.to_room_state(),
                }

    player = room.add_player(
        PlayerInfo(
            id=0,
            name=payload.player_name,
            character_name=payload.character_name,
            is_host=payload.role == "host",
        )
    )
    room.turn_manager.context_manager.characters.append(player)

    return {
        "player_id": RoomRuntimeInfo._format_player_id(player.id),
        "room_state": room.to_room_state(),
    }


@app.post("/api/rooms/{room_id}/actions")
def player_action(room_id: str, payload: PlayerActionRequest):
    room = _get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = parse_player_id(payload.player_id)

    if player_id not in room.players:
        raise HTTPException(status_code=404, detail="player not found")

    action = PlayerAction(
        player_id=payload.player_id,
        character_name=payload.character_name,
        action_text=payload.action_text,
    )
    room.player_action(player_id, action)
    return room.to_room_state()


@app.post("/api/rooms/{room_id}/ready")
def player_ready(room_id: str, payload: PlayerReadyRequest):
    room = _get_room(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = parse_player_id(payload.player_id)

    if player_id not in room.players:
        raise HTTPException(status_code=404, detail="player not found")

    room.change_player_status(player_id, payload.ready)
    return room.to_room_state()


@app.post("/api/host/resolve-turn")
def resolve_turn(payload: HostResolveRequest):
    room = _get_room(payload.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    if payload.force:
        room.resolve_turn(host_note=payload.host_note, force=True)
    else:
        resolved = room.try_resolve_turn(host_note=payload.host_note)
        if not resolved:
            raise HTTPException(status_code=409, detail="not all players are ready")

    return room.to_room_state()


@app.post("/api/host/rollback")
def rollback(payload: HostRollBackRequest):
    room = _get_room(payload.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    room.phase = "planning"
    return room.to_room_state()
