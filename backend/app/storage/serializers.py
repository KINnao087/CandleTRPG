from typing import Any, Mapping

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene, TurnHistory, World
from backend.app.domain.room import Abilities, PlayerInfo, SubAbilities


def world_to_dict(world: World) -> dict[str, Any]:
    return {
        "title": world.title,
        "setting": world.setting,
    }


def dict_to_world(data: Mapping[str, Any] | None) -> World:
    data = data or {}
    return World(
        title=str(data.get("title", "")),
        setting=str(data.get("setting", "")),
    )


def scene_to_dict(scene: Scene) -> dict[str, Any]:
    return {
        "time": scene.time,
        "location": scene.location,
        "description": scene.description,
    }


def dict_to_scene(data: Mapping[str, Any] | None) -> Scene:
    return Scene.from_dict(data or {})


def player_action_to_dict(action: PlayerAction) -> dict[str, Any]:
    return {
        "player_id": action.player_id,
        "character_name": action.character_name,
        "action_text": action.action_text,
    }


def dict_to_player_action(data: Mapping[str, Any] | None) -> PlayerAction:
    data = data or {}
    return PlayerAction(
        player_id=str(data.get("player_id", "")),
        character_name=str(data.get("character_name", "")),
        action_text=str(data.get("action_text", "")),
    )


def sub_abilities_to_dict(sub_abilities: SubAbilities) -> dict[str, Any]:
    return sub_abilities.to_dict()


def dict_to_sub_abilities(data: Mapping[str, Any] | None) -> SubAbilities:
    return SubAbilities.from_dict(dict(data or {}))


def abilities_to_dict(abilities: Abilities) -> dict[str, Any]:
    return abilities.to_dict()


def dict_to_abilities(data: Mapping[str, Any] | None) -> Abilities:
    return Abilities.from_dict(dict(data or {}))


def player_info_to_dict(player: PlayerInfo) -> dict[str, Any]:
    return {
        "id": player.id,
        "name": player.name,
        "character_name": player.character_name,
        "inventory": list(player.inventory),
        "inventory_limits": player.inventory_limits,
        "status": dict(player.status),
        "abilities": [
            abilities_to_dict(ability)
            for ability in player.abilities
        ],
        "is_online": player.is_online,
        "is_host": player.is_host,
    }


def dict_to_player_info(data: Mapping[str, Any] | None) -> PlayerInfo:
    data = data or {}
    return PlayerInfo(
        id=_parse_int(data.get("id", data.get("player_id")), default=0),
        name=str(data.get("name", "")),
        character_name=str(data.get("character_name", "")),
        inventory=_string_list(data.get("inventory", [])),
        inventory_limits=_parse_int(data.get("inventory_limits", 5), default=5),
        status=_dict_or_default(data.get("status"), {
            "hp": 100,
            "conditions": [],
        }),
        abilities=[
            dict_to_abilities(ability)
            for ability in _dict_list(data.get("abilities", []))
        ],
        is_online=_parse_bool(data.get("is_online", True), default=True),
        is_host=_parse_bool(data.get("is_host", False), default=False),
    )


def turn_history_to_dict(turn_history: TurnHistory) -> dict[str, Any]:
    return {
        "turn_index": turn_history.turn_index,
        "actions": [
            player_action_to_dict(action)
            for action in turn_history.actions
        ],
        "narration": turn_history.narration,
        "scene": scene_to_dict(turn_history.scene),
        "character_updates": [
            dict(update)
            for update in turn_history.character_updates
            if isinstance(update, Mapping)
        ],
    }


def dict_to_turn_history(data: Mapping[str, Any] | None) -> TurnHistory:
    data = data or {}
    return TurnHistory(
        turn_index=_parse_int(data.get("turn_index", 0), default=0),
        actions=[
            dict_to_player_action(action)
            for action in _dict_list(data.get("actions", []))
        ],
        narration=str(data.get("narration", "")),
        scene=dict_to_scene(data.get("scene")),
        character_updates=[
            dict(update)
            for update in _dict_list(data.get("character_updates", []))
        ],
    )


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    return [
        dict(item)
        for item in value
        if isinstance(item, Mapping)
    ]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [
        str(item)
        for item in value
    ]


def _dict_or_default(value: Any, default: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)

    return dict(default)


def _parse_int(value: Any, default: int) -> int:
    if isinstance(value, str):
        value = value.removeprefix("player_").removeprefix("char_")

    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y"}:
            return True
        if normalized in {"false", "0", "no", "n"}:
            return False

    return default
