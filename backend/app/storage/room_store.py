from typing import Any, Mapping

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import World
from backend.app.domain.room import PlayerInfo
from backend.app.services.context_manager import ContextManager
from backend.app.services.turn_manager import TurnManager
from backend.app.storage.serializers import (
    dict_to_player_action,
    dict_to_player_info,
    dict_to_scene,
    dict_to_turn_history,
    dict_to_world,
    player_action_to_dict,
    player_info_to_dict,
    scene_to_dict,
    turn_history_to_dict,
    world_to_dict,
)

#内存运行时房间信息
class RoomRuntimeInfo:
    room_id: str
    phase: str
    players: dict[int, PlayerInfo]
    actions: dict[int, PlayerAction]
    player_status: dict[int, bool]
    timeline: list[dict[str, Any]]
    world: World
    turn_manager: TurnManager

    def __init__(
        self,
        room_id: str,
        phase: str,
        turn_manager: TurnManager,
        world: World | None = None,
    ):
        self.room_id = room_id
        self.phase = phase
        self.turn_manager = turn_manager
        self.world = world or World(title="", setting="")
        self.players = {}
        self.actions = {}
        self.player_status = {}
        self.timeline = []
        self._next_player_id = 1

    def add_player(self, player: PlayerInfo) -> PlayerInfo:
        player.id = self._next_player_id
        player.is_online = True
        self._next_player_id += 1

        self.players[player.id] = player
        self.player_status[player.id] = False
        return player

    def find_player(self, player_name: str, character_name: str) -> PlayerInfo | None:
        for player in self.players.values():
            if player.name == player_name and player.character_name == character_name:
                return player
        return None

    def mark_player_online(self, player_id: int) -> PlayerInfo | None:
        player = self.players.get(player_id)
        if player is None:
            return None

        player.is_online = True
        self.actions.pop(player_id, None)
        self.player_status[player_id] = False
        return player

    def mark_player_offline(self, player_id: int) -> PlayerInfo | None:
        player = self.players.get(player_id)
        if player is None:
            return None

        player.is_online = False
        self.actions.pop(player_id, None)
        self.player_status[player_id] = False
        return player

    def get_online_players(self) -> list[PlayerInfo]:
        return [
            player
            for player in self.players.values()
            if player.is_online
        ]

    def remove_player(self, player_id: int) -> PlayerInfo | None:
        player = self.players.pop(player_id, None)
        if player is None:
            return None

        self.player_status.pop(player_id, None)
        self.actions.pop(player_id, None)

        context = self.turn_manager.context_manager
        context.characters = [
            character for character in context.characters
            if character.id != player_id
        ]

        return player

    def player_action(self, player_id: int, action: PlayerAction) -> None:
        self.actions[player_id] = action

    def change_player_status(self, player_id: int, status: bool) -> None:
        self.player_status[player_id] = status

    def try_resolve_turn(self, host_note: str = "") -> bool:
        for player in self.get_online_players():
            if not self.player_status.get(player.id, False):
                return False

        self.resolve_turn(host_note=host_note)
        return True

    def resolve_turn(self, host_note: str = "", force: bool = False) -> None:
        self.phase = "resolving"
        turn_index = self.turn_manager.turn_index
        result = self.turn_manager.resolve_turn(
            actions=self._build_turn_actions(force=force),
            host_note=host_note,
            active_characters=self.get_online_players(),
        )

        self.timeline.insert(0, {
            "id": f"event_{turn_index:03d}",
            "type": "turn_resolved",
            "title": f"第 {turn_index} 回合结算",
            "content": result.narration,
            "timestamp": result.scene.time,
        })

        self.actions.clear()

        for player_id in self.player_status:
            self.player_status[player_id] = False

        self.phase = "planning"

    def _build_turn_actions(self, force: bool) -> list[PlayerAction]:
        actions = []
        for player in self.get_online_players():
            player_id = player.id
            action = self.actions.get(player_id)
            if action is not None:
                actions.append(action)
                continue

            if force:
                actions.append(
                    PlayerAction(
                        player_id=self._format_player_id(player_id),
                        character_name=player.character_name,
                        action_text="无动作",
                    )
                )
        return actions

    def to_snapshot(self) -> dict[str, Any]:
        context = self.turn_manager.context_manager

        return {
            "schema_version": 1,
            "room_id": self.room_id,
            "phase": self.phase,
            "next_player_id": self._next_player_id,
            "world": world_to_dict(self.world),
            "scene": scene_to_dict(context.scene),
            "players": [
                player_info_to_dict(player)
                for player in self.players.values()
            ],
            "actions": {
                str(player_id): player_action_to_dict(action)
                for player_id, action in self.actions.items()
            },
            "player_status": {
                str(player_id): ready
                for player_id, ready in self.player_status.items()
            },
            "timeline": [
                dict(event)
                for event in self.timeline
                if isinstance(event, Mapping)
            ],
            "turn_index": self.turn_manager.turn_index,
            "turn_history": [
                turn_history_to_dict(history)
                for history in context.turn_history
            ],
            "recent_summary": getattr(context, "recent_summary", ""),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, Any]) -> "RoomRuntimeInfo":
        world = dict_to_world(data.get("world"))
        players = [
            dict_to_player_info(player)
            for player in cls._dict_list(data.get("players", []))
        ]
        context = ContextManager(
            world=world,
            scene=dict_to_scene(data.get("scene")),
            characters=players,
        )
        context.turn_history = [
            dict_to_turn_history(history)
            for history in cls._dict_list(data.get("turn_history", []))
        ]
        context.recent_summary = str(data.get("recent_summary", ""))

        turn_manager = TurnManager(context)
        turn_manager.turn_index = cls._parse_int(data.get("turn_index", 1), default=1)

        room = cls(
            room_id=str(data.get("room_id", "")),
            phase=str(data.get("phase", "planning")),
            turn_manager=turn_manager,
            world=world,
        )
        room.players = {
            player.id: player
            for player in players
        }
        room.actions = cls._restore_actions(data.get("actions", {}))
        room.player_status = cls._restore_player_status(data.get("player_status", {}))

        for player_id in room.players:
            room.player_status.setdefault(player_id, False)

        room.timeline = [
            dict(event)
            for event in cls._dict_list(data.get("timeline", []))
        ]
        room._next_player_id = cls._parse_int(
            data.get("next_player_id"),
            default=(max(room.players.keys(), default=0) + 1),
        )
        return room

    def to_room_state(self) -> dict[str, Any]:
        context = self.turn_manager.context_manager
        online_players = self.get_online_players()

        return {
            "room_id": self.room_id,
            "turn_index": self.turn_manager.turn_index,
            "phase": self.phase,
            "world": {
                "title": self.world.title,
                "setting": self.world.setting,
            },
            "scene": {
                "time": context.scene.get("time", ""),
                "location": context.scene.get("location", ""),
                "description": context.scene.get("description", ""),
            },
            "players": [
                {
                    "id": self._format_player_id(player.id),
                    "name": player.name,
                    "character_name": player.character_name,
                    "role": "host" if player.is_host else "player",
                    "ready": self.player_status.get(player.id, False),
                    "action_text": self.actions[player.id].action_text if player.id in self.actions else "",
                }
                for player in online_players
            ],
            "characters": self._format_characters(online_players),
            "timeline": self.timeline,
        }

    @staticmethod
    def _format_player_id(player_id: int) -> str:
        return f"player_{player_id:03d}"

    @staticmethod
    def _parse_int(value: Any, default: int) -> int:
        if isinstance(value, str):
            value = value.removeprefix("player_").removeprefix("char_")

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @classmethod
    def _restore_actions(cls, value: Any) -> dict[int, PlayerAction]:
        if not isinstance(value, Mapping):
            return {}

        actions: dict[int, PlayerAction] = {}
        for player_id, action_data in value.items():
            if not isinstance(action_data, Mapping):
                continue

            actions[cls._parse_int(player_id, default=0)] = dict_to_player_action(action_data)

        return {
            player_id: action
            for player_id, action in actions.items()
            if player_id > 0
        }

    @classmethod
    def _restore_player_status(cls, value: Any) -> dict[int, bool]:
        if not isinstance(value, Mapping):
            return {}

        return {
            cls._parse_int(player_id, default=0): bool(ready)
            for player_id, ready in value.items()
            if cls._parse_int(player_id, default=0) > 0
        }

    @staticmethod
    def _dict_list(value: Any) -> list[dict[str, Any]]:
        if not isinstance(value, list):
            return []

        return [
            dict(item)
            for item in value
            if isinstance(item, Mapping)
        ]

    @staticmethod
    def _format_characters(characters: list[PlayerInfo]) -> list[dict[str, Any]]:
        return [
            {
                "id": f"char_{character.id:03d}",
                "player_id": RoomRuntimeInfo._format_player_id(character.id),
                "name": character.character_name,
                "status": character.status,
                "inventory": character.inventory,
                "abilities": [
                    ability.to_dict()
                    for ability in character.abilities
                ],
            }
            for character in characters
        ]




class RoomStore:
    def __init__(self):
        self.rooms: dict[str, RoomRuntimeInfo] = {}

    def add_room(self, room: RoomRuntimeInfo) -> None:
        self.rooms[room.room_id] = room

    def get_room(self, room_id: str) -> RoomRuntimeInfo | None:
        return self.rooms.get(room_id)
