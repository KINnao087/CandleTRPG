from fastapi import FastAPI, HTTPException
from starlette.middleware.cors import CORSMiddleware

from backend.app.ai.resolve_turn_graph import build_resolve_turn_graph
from backend.app.domain.action import PlayerAction
from backend.app.domain.api import (
    HostResolveRequest,
    HostRollBackRequest,
    JoinRequest,
    LeaveRequest,
    PlayerActionRequest,
    PlayerReadyRequest,
    CreateRoomRequest,
    WorldRequest,
)
from backend.app.domain.context import Scene, World
from backend.app.domain.error import RoomNotFoundError
from backend.app.domain.room import PlayerInfo
from backend.app.services.context_manager import ContextManager
from backend.app.services.turn_manager import TurnManager
from backend.app.storage.room_persistence import RoomPersistence
from backend.app.storage.room_store import RoomRuntimeInfo, RoomStore
from backend.app.ws.web_socket import RoomConnectionManager

app = FastAPI(title="CandleTRPG-LAN")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

room_store = RoomStore()
room_persistence = RoomPersistence()
connection_manager = RoomConnectionManager()

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


def _get_room(room_hash: str) -> RoomRuntimeInfo | None:
    """获取一个房间的管理器"""
    return room_store.get_room(room_hash)


def _get_or_load_room(room_hash: str) -> RoomRuntimeInfo | None:
    room = _get_room(room_hash)
    if room is not None:
        return room

    room = room_persistence.load_latest_room(room_hash)
    if room is not None:
        room_store.add_room(room)

    return room


def room_hash_exists(room_hash: str) -> bool:
    return room_store.has_room_hash(room_hash) or room_persistence.has_room_hash(room_hash)


async def _broadcast_room_state(room: RoomRuntimeInfo) -> dict:
    room_state = room.to_room_state()
    await connection_manager.broadcast_room_state(room.room.room_hash, room_state)
    return room_state


def _create_room(room_id: str, room_hash: str, payload: CreateRoomRequest) -> RoomRuntimeInfo:
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
        world=world,
        opening_scene=payload.world.opening_scene,
        room_hash=room_hash,
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
    room.update_world(
        world=World(title=payload.title, setting=payload.setting),
        opening_scene=payload.opening_scene,
    )

def parse_player_id(player_id: str) -> int:
    if player_id.startswith("player_"):
        return int(player_id.removeprefix("player_"))
    return int(player_id)


@app.get("/api/health")
def health():
    return {"status": "ok"}

#创建房间，如果存在就返回错误
@app.post("/api/rooms/{room_id}")
async def create_room(room_id: str, payload: CreateRoomRequest):
    room_hash = RoomRuntimeInfo.build_room_hash(room_id)
    room = _get_or_load_room(room_hash)

    if room is not None:
        raise HTTPException(status_code=409, detail="Room already exists")

    if room_hash_exists(room_hash):
        raise HTTPException(status_code=409, detail="Room hash already exists")

    room = _create_room(room_id, room_hash, payload)
    room_store.add_room(room)
    room_persistence.append_event(room, "room_created", {
        "host_name": payload.host_name,
        "character_name": payload.character_name,
        "world": {
            "title": payload.world.title,
            "setting": payload.world.setting,
            "opening_scene": payload.world.opening_scene,
        },
    })
    room_persistence.save_initial_room(room)

    host = next(player for player in room.players.values() if player.is_host)
    room.mark_player_online(host.id)
    room_persistence.save_room(room)
    room_state = await _broadcast_room_state(room)
    return {
        "player_id": RoomRuntimeInfo._format_player_id(host.id),
        "room_state": room_state,
    }


@app.post("/api/rooms/{room_hash}/world")
async def import_world(room_hash: str, payload: WorldRequest):
    room = _get_or_load_room(room_hash)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    _update_room_world(room, payload)
    room_persistence.append_event(room, "world_updated", {
        "title": payload.title,
        "setting": payload.setting,
        "opening_scene": payload.opening_scene,
    })
    room_persistence.save_room(room)
    return {
        "room_state": await _broadcast_room_state(room),
    }


@app.get("/api/rooms/{room_hash}/state")
def get_room_state(room_hash: str):
    room = _get_or_load_room(room_hash)
    if room is None:
        return None
    return room.to_room_state()


@app.post("/api/rooms/{room_hash}/join")
async def join_room(room_hash: str, payload: JoinRequest):
    room = _get_or_load_room(room_hash)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    if payload.role == "host":
        for current_player in room.players.values():
            if current_player.is_host:
                room.mark_player_online(current_player.id)
                room_persistence.append_event(room, "player_reconnected", {
                    "player_id": RoomRuntimeInfo._format_player_id(current_player.id),
                    "player_name": current_player.name,
                    "character_name": current_player.character_name,
                    "role": "host",
                })
                room_persistence.save_room(room)
                room_state = await _broadcast_room_state(room)
                return {
                    "player_id": RoomRuntimeInfo._format_player_id(current_player.id),
                    "room_state": room_state,
                }

    player = room.find_player(
        player_name=payload.player_name,
        character_name=payload.character_name,
    )
    if player is not None:
        if player.is_online:
            raise HTTPException(status_code=409, detail="player already online")

        room.mark_player_online(player.id)
        room_persistence.append_event(room, "player_reconnected", {
            "player_id": RoomRuntimeInfo._format_player_id(player.id),
            "player_name": player.name,
            "character_name": player.character_name,
            "role": "host" if player.is_host else "player",
        })
        room_persistence.save_room(room)
        room_state = await _broadcast_room_state(room)
        return {
            "player_id": RoomRuntimeInfo._format_player_id(player.id),
            "room_state": room_state,
        }

    player = room.add_player(
        PlayerInfo(
            id=0,
            name=payload.player_name,
            character_name=payload.character_name,
            is_host=payload.role == "host",
        )
    )

    room_persistence.append_event(room, "player_joined", {
        "player_id": RoomRuntimeInfo._format_player_id(player.id),
        "player_name": player.name,
        "character_name": player.character_name,
        "role": "host" if player.is_host else "player",
    })
    room_persistence.save_room(room)
    room_state = await _broadcast_room_state(room)
    return {
        "player_id": RoomRuntimeInfo._format_player_id(player.id),
        "room_state": room_state,
    }


@app.post("/api/rooms/{room_hash}/leave")
async def leave_room(room_hash: str, payload: LeaveRequest):
    room = _get_or_load_room(room_hash)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = parse_player_id(payload.player_id)
    player = room.mark_player_offline(player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="player not found")

    room_persistence.append_event(room, "player_left", {
        "player_id": payload.player_id,
        "player_name": player.name,
        "character_name": player.character_name,
    })
    room_persistence.save_room(room)
    return await _broadcast_room_state(room)


@app.post("/api/rooms/{room_hash}/actions")
async def player_action(room_hash: str, payload: PlayerActionRequest):
    room = _get_or_load_room(room_hash)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = parse_player_id(payload.player_id)

    if player_id not in room.players:
        raise HTTPException(status_code=404, detail="player not found")
    if not room.players[player_id].is_online:
        raise HTTPException(status_code=409, detail="player is offline")

    action = PlayerAction(
        player_id=payload.player_id,
        character_name=payload.character_name,
        action_text=payload.action_text,
    )
    room.player_action(player_id, action)
    room_persistence.append_event(room, "player_action_submitted", {
        "player_id": payload.player_id,
        "character_name": payload.character_name,
        "action_text": payload.action_text,
        "turn_index": payload.turn_index,
    })
    room_persistence.save_room(room)
    return await _broadcast_room_state(room)


@app.post("/api/rooms/{room_hash}/ready")
async def player_ready(room_hash: str, payload: PlayerReadyRequest):
    room = _get_or_load_room(room_hash)
    if room is None:
        raise HTTPException(status_code=404, detail="room not found")

    player_id = parse_player_id(payload.player_id)

    if player_id not in room.players:
        raise HTTPException(status_code=404, detail="player not found")
    if not room.players[player_id].is_online:
        raise HTTPException(status_code=409, detail="player is offline")

    room.change_player_status(player_id, payload.ready)
    room_persistence.append_event(room, "ready_updated", {
        "player_id": payload.player_id,
        "ready": payload.ready,
    })
    room_persistence.save_room(room)
    return await _broadcast_room_state(room)


rt_graph = build_resolve_turn_graph(
    room_persistence=room_persistence,
    room_store=room_store,
)
@app.post("/api/host/resolve-turn")
async def resolve_turn(payload: HostResolveRequest):
    try:
        result = rt_graph.invoke({
            "room_hash": payload.room_hash,
            "host_note": payload.host_note,
            "force": payload.force,
            "workflow_status": "loading",
        })
    except RoomNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    status = result["workflow_status"]

    if status == "rejected":
        raise HTTPException(
            status_code=409,
            detail={
                "message": "当前回合无法结算",
                "errors": result.get("validation_errors", []),
            },
        )

    if status == "failed":
        raise HTTPException(
            status_code=500,
            detail={
                "message": "回合结算失败",
                "errors": result.get("validation_errors", []),
            },
        )

    room = room_store.get_room(payload.room_hash)
    if room is None:
        raise HTTPException(
            status_code=404,
            detail="room not found",
        )

    return await _broadcast_room_state(room)


@app.post("/api/host/rollback")
async def rollback(payload: HostRollBackRequest):
    room = room_persistence.rollback_room(payload.room_hash, payload.turn_index)
    if room is None:
        raise HTTPException(status_code=404, detail="snapshot not found")

    room_store.add_room(room)
    room_persistence.append_event(room, "rollback", {
        "target_turn_index": payload.turn_index,
    })
    room_persistence.save_room(room)
    return await _broadcast_room_state(room)

@app.get("/api/saved-rooms")
def list_saved_rooms():
    return {"rooms":room_persistence.list_saved_rooms()}

from fastapi import WebSocket, WebSocketDisconnect
@app.websocket("/ws/rooms/{room_hash}")
async def room_socket(websocket: WebSocket, room_hash: str, player_id: str | None = None):
    await connection_manager.connect(room_hash, websocket)

    room = _get_or_load_room(room_hash)
    if room is not None:
        await websocket.send_json({
            "type": "room_state",
            "room_id": room.room_id,
            "room_hash": room.room.room_hash,
            "payload": room.to_room_state(),
        })

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connection_manager.disconnect(room_hash, websocket)
