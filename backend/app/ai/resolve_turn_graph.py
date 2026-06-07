from copy import deepcopy
from typing import Any, Literal, TypedDict, Callable

from backend.app.ai.gm_graph import build_gm_graph
from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene, TurnHistory, TurnResult, World
from backend.app.domain.error import RoomNotFoundError
from backend.app.domain.room import PlayerInfo
from backend.app.storage.room_persistence import RoomPersistence
from backend.app.storage.room_store import RoomStore


class ResolveTurnState(TypedDict, total=False):
    # 回合结算请求
    resolution_id: str
    room_id: str
    room_hash: str
    turn_index: int
    force: bool
    host_note: str

    # 本次结算使用的不可变房间快照
    room_phase: str
    room_updated_at: str
    world: World
    scene: Scene
    players: list[PlayerInfo]
    history: list[TurnHistory]
    ready_status: dict[int, bool]
    submitted_actions: dict[int, PlayerAction]
    player_actions: list[PlayerAction]

    # GM 子图的输入与输出
    prompt: str
    raw_response: str
    narration: str
    scene_update: dict[str, Any]
    character_updates: list[dict[str, Any]]
    turn_result: TurnResult

    # 工作流控制
    workflow_status: Literal[
        "loading",
        "validating",
        "resolving",
        "reviewing",
        "committing",
        "completed",
        "rejected",
        "failed",
    ]
    can_resolve: bool
    validation_errors: list[str]
    retry_count: int
    max_retries: int
    error: str | None

    # 提交结果与 API 输出
    timeline_event: dict[str, Any]
    committed: bool
    room_state: dict[str, Any]

def create_load_room_snapshot_node(
      room_store: RoomStore,
      room_persistence: RoomPersistence,
) -> Callable[[ResolveTurnState], dict[str, Any]]:
    def load_room_snapshot(state: ResolveTurnState) -> dict[str, Any]:
        room_hash = state["room_hash"]

        runtime = room_store.get_room(room_hash)
        if runtime is None:
            runtime = room_persistence.load_latest_room(room_hash)
            if runtime is None:
                raise RoomNotFoundError(f"房间不存在: {room_hash}")
            #将房间重新放入内存
            room_store.add_room(runtime)

        room = runtime.room
        context = runtime.turn_manager.context_manager
        return {"turn_index": runtime.turn_manager.turn_index, "room_phase": room.phase,
                "room_updated_at": room.updated_at, "world": deepcopy(context.world),
                "scene": deepcopy(context.scene), "players": deepcopy(context.characters),
                "history": deepcopy(context.turn_history), "ready_status": deepcopy(room.player_status),
                "submitted_actions": deepcopy(room.actions), "workflow_status": "validating", "can_resolve": False,
                "validation_errors": [], "retry_count": 0, "max_retries": 2, "error": None, "committed": False,
                "room_id": room.room_id, "room_hash": room_hash
        }

    return load_room_snapshot

def check_resolve_condition(state: ResolveTurnState) -> dict[str, Any]:
    characters = state["players"]
    validation_errors = []

    if state["room_phase"] != "planning":
        validation_errors.append("房间当前不处于行动规划阶段")
    if not any(character.is_online for character in characters):
        validation_errors.append("房间内没有在线玩家")

    if validation_errors:
        return {
            "can_resolve": False,
            "workflow_status": "rejected",
            "validation_errors": validation_errors,
        }

    force = state["force"]
    if force:
        return {
            "can_resolve": True,
            "workflow_status": "validating",
            "validation_errors": [],
        }

    status = state["ready_status"]
    for character in characters:
        if status[character.id] is not True and character.is_online is True:
            return {
                "can_resolve": False,
                "workflow_status": "rejected",
                "validation_errors": ["仍有在线玩家未准备"],
            }

    return {
        "can_resolve": True,
        "workflow_status": "validating",
        "validation_errors": [],
    }

#处理玩家提交过来的动作
def normalize_actions(state: ResolveTurnState) -> dict[str, Any]:
    player_actions = []
    ready_status = state["ready_status"]
    for player in state["players"]:
        if not player.is_online:
            continue
        if ready_status[player.id]:
            player_actions.append(state["submitted_actions"][player.id])
        else:
            player_actions.append(PlayerAction(player_id=player.player_id, character_name=player.character_name, action_text="无动作"))

    return {"player_actions": player_actions}

def run_gm(state: ResolveTurnState) -> dict[str, Any]:
    world = state["world"]

    gm_graph = build_gm_graph()

    world_text = f"{world.title}\n{world.setting}"
    gm_result = gm_graph.invoke({
        "world": world_text,
        "scene": state["scene"],
        "characters": [
          player
          for player in state["players"]
          if player.is_online
        ],
        "history": state["history"],
        "player_actions": state["player_actions"],
        "host_note": state.get("host_note", ""),
    })

    return {
        "raw_response": gm_result.get("raw_response", ""),
        "narration": gm_result.get("narration", ""),
        "scene_update": gm_result.get("scene_update", {}),
        "character_updates": gm_result.get(
            "character_updates",
            [],
        ),
        "workflow_status": "reviewing",
    }


def validate_gm_result(state: ResolveTurnState) -> dict[str, Any]:
    validation_errors: list[str] = []

    narration = state.get("narration")
    if not isinstance(narration, str) or not narration.strip():
        validation_errors.append("GM 返回的旁白为空")

    scene_update = state.get("scene_update")
    if not isinstance(scene_update, dict):
        validation_errors.append("GM 返回的场景更新不是对象")
    else:
        for field_name, display_name in (
            ("time", "时间"),
            ("location", "地点"),
            ("description", "场景描述"),
        ):
            value = scene_update.get(field_name)
            if not isinstance(value, str) or not value.strip():
                validation_errors.append(f"GM 返回的场景{display_name}为空")

    character_updates = state.get("character_updates")
    if not isinstance(character_updates, list):
        validation_errors.append("GM 返回的角色更新不是列表")
    else:
        players = state.get("players", [])
        valid_character_ids = {player.character_id for player in players}
        valid_player_ids = {player.player_id for player in players}
        valid_character_names = {player.character_name for player in players}

        for index, update in enumerate(character_updates):
            item_name = f"第 {index + 1} 条角色更新"
            if not isinstance(update, dict):
                validation_errors.append(f"{item_name}不是对象")
                continue

            character_id = update.get("character_id")
            player_id = update.get("player_id")
            character_name = update.get("character_name")

            has_valid_target = (
                character_id in valid_character_ids
                or player_id in valid_player_ids
                or character_name in valid_character_names
            )
            if not has_valid_target:
                validation_errors.append(f"{item_name}未指向房间中的角色")

            for field_name in ("status", "status_delta"):
                value = update.get(field_name)
                if value is not None and not isinstance(value, dict):
                    validation_errors.append(
                        f"{item_name}的 {field_name} 不是对象"
                    )

            for field_name in (
                "inventory",
                "inventory_add",
                "inventory_remove",
                "abilities",
            ):
                value = update.get(field_name)
                if value is not None and not isinstance(value, list):
                    validation_errors.append(
                        f"{item_name}的 {field_name} 不是列表"
                    )

    if not validation_errors:
        return {
            "validation_errors": [],
            "error": None,
            "workflow_status": "reviewing",
        }

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    error = "; ".join(validation_errors)

    if retry_count < max_retries:
        return {
            "validation_errors": validation_errors,
            "error": error,
            "retry_count": retry_count + 1,
            "workflow_status": "resolving",
        }

    return {
        "validation_errors": validation_errors,
        "error": error,
        "workflow_status": "failed",
    }


def build_turn_result(state: ResolveTurnState) -> dict[str, Any]:
    turn_result = TurnResult.from_ai_state({
        "narration": state["narration"],
        "scene_update": state["scene_update"],
        "character_updates": state["character_updates"],
        "raw_response": state.get("raw_response", ""),
    })

    return {
        "turn_result": turn_result,
        "workflow_status": "committing",
    }


def create_commit_resolution_node(
    room_store: RoomStore,
    room_persistence: RoomPersistence,
) -> Callable[[ResolveTurnState], dict[str, Any]]:
    def commit_resolution(state: ResolveTurnState) -> dict[str, Any]:
        room_hash = state["room_hash"]
        runtime = room_store.get_room(room_hash)
        if runtime is None:
            raise RoomNotFoundError(f"房间不存在: {room_hash}")

        room = runtime.room
        turn_index = state["turn_index"]

        if runtime.turn_manager.turn_index != turn_index:
            error = "回合编号已经变化，当前结算结果已过期"
            return {
                "committed": False,
                "workflow_status": "failed",
                "validation_errors": [error],
                "error": error,
            }

        if room.updated_at != state["room_updated_at"]:
            error = "房间状态已经变化，当前结算结果已过期"
            return {
                "committed": False,
                "workflow_status": "failed",
                "validation_errors": [error],
                "error": error,
            }

        turn_result = state["turn_result"]
        context = runtime.turn_manager.context_manager

        runtime.phase = "resolving"
        context.record_turn(
            turn_index=turn_index,
            actions=state["player_actions"],
            result=turn_result,
        )
        runtime.turn_manager.turn_index += 1

        timeline_event = {
            "id": f"event_{turn_index:03d}",
            "type": "turn_resolved",
            "title": f"第 {turn_index} 回合结算",
            "content": turn_result.narration,
            "timestamp": turn_result.scene.time,
        }
        runtime.timeline.insert(0, timeline_event)

        runtime.actions.clear()
        for player_id in runtime.player_status:
            runtime.player_status[player_id] = False

        runtime.phase = "planning"
        runtime._sync_room_from_runtime(touch=True)

        room_persistence.append_event(runtime, "turn_resolved", {
            "timeline_event": timeline_event,
            "scene": {
                "time": turn_result.scene.time,
                "location": turn_result.scene.location,
                "description": turn_result.scene.description,
            },
            "character_updates": turn_result.character_updates,
            "narration": turn_result.narration,
        })
        room_persistence.save_turn_snapshot(runtime)

        return {
            "timeline_event": timeline_event,
            "committed": True,
            "workflow_status": "committing",
            "validation_errors": [],
            "error": None,
        }

    return commit_resolution


def create_build_response_node(
    room_store: RoomStore,
) -> Callable[[ResolveTurnState], dict[str, Any]]:
    def build_response(state: ResolveTurnState) -> dict[str, Any]:
        room_hash = state["room_hash"]
        runtime = room_store.get_room(room_hash)
        if runtime is None:
            raise RoomNotFoundError(f"房间不存在: {room_hash}")

        if not state.get("committed", False):
            error = state.get("error") or "回合结算结果尚未提交"
            return {
                "workflow_status": "failed",
                "error": error,
            }

        return {
            "room_state": runtime.to_room_state(),
            "workflow_status": "completed",
            "error": None,
        }

    return build_response

from langgraph.graph import START, END, StateGraph
def route_after_condition_check(state: ResolveTurnState) -> str:
    if state["can_resolve"]:
        return "continue"
    return "reject"

def route_after_gm_validation(state: ResolveTurnState) -> str:
    status = state["workflow_status"]

    if status == "reviewing":
        return "continue"

    if status == "resolving":
        return "retry"

    return "fail"

def route_after_commit(state: ResolveTurnState) -> str:
    if state["committed"]:
        return "continue"
    return "fail"

def build_resolve_turn_graph(
    room_store: RoomStore,
    room_persistence: RoomPersistence,
):
    graph = StateGraph(ResolveTurnState)

    graph.add_node("load_room_snapshot",create_load_room_snapshot_node(room_store=room_store,room_persistence=room_persistence))
    graph.add_node("check_resolve_condition", check_resolve_condition)
    graph.add_node("normalize_actions", normalize_actions)
    graph.add_node("run_gm", run_gm)
    graph.add_node("validate_gm_result", validate_gm_result)
    graph.add_node("build_turn_result", build_turn_result)
    graph.add_node("commit_resolution", create_commit_resolution_node(room_store=room_store, room_persistence=room_persistence))
    graph.add_node("build_response", create_build_response_node(room_store=room_store))

    graph.add_edge(START, "load_room_snapshot")
    graph.add_edge("load_room_snapshot", "check_resolve_condition")
    graph.add_conditional_edges(
        "check_resolve_condition",
       route_after_condition_check,
       {
           "continue": "normalize_actions",
           "reject": END,
       }
    )
    graph.add_edge("normalize_actions", "run_gm")
    graph.add_edge("run_gm", "validate_gm_result")
    graph.add_conditional_edges(
        "validate_gm_result",
        route_after_gm_validation,
        {
            "continue": "build_turn_result",
            "retry": "run_gm", "fail": END,
        },
    )
    graph.add_edge("build_turn_result", "commit_resolution", )
    graph.add_conditional_edges(
        "commit_resolution",
        route_after_commit,
        {
            "continue": "build_response",
            "fail": END,
        },
    )
    graph.add_edge("build_response", END, )

    return graph.compile()
