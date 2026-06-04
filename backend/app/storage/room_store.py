import hashlib
import json
from typing import Any, Mapping

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene, World
from backend.app.domain.room import PlayerInfo, Room
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
    room: Room
    turn_manager: TurnManager

    # Compatibility proxy fields backed by self.room.
    room_id: str
    phase: str
    world: World
    players: dict[int, PlayerInfo]
    actions: dict[int, PlayerAction]
    player_status: dict[int, bool]
    timeline: list[dict[str, Any]]
    _next_player_id: int

    def __init__(
        self,
        room_id: str,
        phase: str,
        turn_manager: TurnManager,
        world: World | None = None,
        room: Room | None = None,
        opening_scene: str = "",
    ):
        context = turn_manager.context_manager
        self.room: Room = room or Room(
            room_id=room_id,
            phase=phase,
            world=world or context.world,
            opening_scene=opening_scene or context.scene.description,
            scene=context.scene,
            turn_index=turn_manager.turn_index,
            turn_history=list(context.turn_history),
            recent_summary=getattr(context, "recent_summary", ""),
        )
        self.turn_manager: TurnManager = turn_manager
        self._sync_runtime_from_room()

    @property
    def room_id(self) -> str:
        return self.room.room_id

    @property
    def phase(self) -> str:
        return self.room.phase

    @phase.setter
    def phase(self, value: str) -> None:
        self.room.phase = value

    @property
    def world(self) -> World:
        return self.room.world

    @world.setter
    def world(self, value: World) -> None:
        self.room.world = value

    @property
    def players(self) -> dict[int, PlayerInfo]:
        return self.room.players

    @players.setter
    def players(self, value: dict[int, PlayerInfo]) -> None:
        self.room.players = value

    @property
    def actions(self) -> dict[int, PlayerAction]:
        return self.room.actions

    @actions.setter
    def actions(self, value: dict[int, PlayerAction]) -> None:
        self.room.actions = value

    @property
    def player_status(self) -> dict[int, bool]:
        return self.room.player_status

    @player_status.setter
    def player_status(self, value: dict[int, bool]) -> None:
        self.room.player_status = value

    @property
    def timeline(self) -> list[dict[str, Any]]:
        return self.room.timeline

    @timeline.setter
    def timeline(self, value: list[dict[str, Any]]) -> None:
        self.room.timeline = value

    @property
    def _next_player_id(self) -> int:
        return self.room.next_player_id

    @_next_player_id.setter
    def _next_player_id(self, value: int) -> None:
        self.room.next_player_id = value

    def _sync_runtime_from_room(self) -> None:
        context = self.turn_manager.context_manager
        context.world = self.room.world
        context.scene = self.room.scene
        if self.room.players:
            context.characters = list(self.room.players.values())
        context.turn_history = list(self.room.turn_history)
        context.recent_summary = self.room.recent_summary
        self.turn_manager.turn_index = self.room.turn_index

    def _sync_room_from_runtime(self, *, touch: bool = False) -> None:
        context = self.turn_manager.context_manager
        self.room.world = context.world
        self.room.scene = context.scene
        self.room.players = {
            player.id: player
            for player in context.characters
            if player.id > 0
        } or self.room.players
        self.room.turn_index = self.turn_manager.turn_index
        self.room.turn_history = list(context.turn_history)
        self.room.recent_summary = getattr(context, "recent_summary", "")
        if touch:
            self.room.touch()

    def update_world(self, world: World, opening_scene: str) -> None:
        self.room.world = world
        self.room.opening_scene = opening_scene

        context = self.turn_manager.context_manager
        context.world = world
        context.scene = Scene.from_dict({
            "time": context.scene.get("time", ""),
            "location": context.scene.get("location", ""),
            "description": opening_scene,
        })
        self.room.scene = context.scene

        if self.timeline:
            self.timeline[-1]["content"] = opening_scene
        else:
            self.timeline.append({
                "id": "event_001",
                "type": "scene",
                "title": "当前场景",
                "content": opening_scene,
                "timestamp": context.scene.get("time", ""),
            })

        self.room.touch()

    def add_player(self, player: PlayerInfo) -> PlayerInfo:
        player.id = self._next_player_id
        player.is_online = True
        self._next_player_id += 1

        self.players[player.id] = player
        self.player_status[player.id] = False
        context = self.turn_manager.context_manager
        if all(character is not player for character in context.characters):
            context.characters.append(player)
        if player.is_host:
            self.room.host_player_id = player.id
        self.room.touch()
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
        self.room.touch()
        return player

    def mark_player_offline(self, player_id: int) -> PlayerInfo | None:
        player = self.players.get(player_id)
        if player is None:
            return None

        player.is_online = False
        self.actions.pop(player_id, None)
        self.player_status[player_id] = False
        self.room.touch()
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

        if self.room.host_player_id == player_id:
            self.room.host_player_id = None
        self.room.touch()
        return player

    def player_action(self, player_id: int, action: PlayerAction) -> None:
        self.actions[player_id] = action
        self.room.touch()

    def change_player_status(self, player_id: int, status: bool) -> None:
        self.player_status[player_id] = status
        self.room.touch()

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
        self._sync_room_from_runtime(touch=True)

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
        self._sync_room_from_runtime()
        context = self.turn_manager.context_manager

        snapshot = {
            "schema_version": 2,
            "room_id": self.room_id,
            "room_hash": self.room.room_hash,
            "phase": self.phase,
            "next_player_id": self._next_player_id,
            "host_player_id": self._format_player_id(self.room.host_player_id) if self.room.host_player_id else None,
            "opening_scene": self.room.opening_scene,
            "created_at": self.room.created_at,
            "updated_at": self.room.updated_at,
            "world": {
                **world_to_dict(self.world),
                "opening_scene": self.room.opening_scene,
            },
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
        room_hash = self._calculate_room_hash(snapshot)
        self.room.room_hash = room_hash
        snapshot["room_hash"] = room_hash
        return snapshot

    @classmethod
    def from_snapshot(cls, data: Mapping[str, Any]) -> "RoomRuntimeInfo":
        world = dict_to_world(data.get("world"))
        scene = dict_to_scene(data.get("scene"))
        players = [
            dict_to_player_info(player)
            for player in cls._dict_list(data.get("players", []))
        ]
        context = ContextManager(
            world=world,
            scene=scene,
            characters=players,
        )
        context.turn_history = [
            dict_to_turn_history(history)
            for history in cls._dict_list(data.get("turn_history", []))
        ]
        context.recent_summary = str(data.get("recent_summary", ""))

        turn_manager = TurnManager(context)
        turn_manager.turn_index = cls._parse_int(data.get("turn_index", 1), default=1)

        player_map = {
            player.id: player
            for player in players
        }
        host_player_id = cls._parse_int(data.get("host_player_id"), default=0)
        if host_player_id <= 0:
            host_player_id = next(
                (player.id for player in players if player.is_host),
                0,
            )

        world_data = data.get("world")
        if not isinstance(world_data, Mapping):
            world_data = {}
        opening_scene = str(
            data.get("opening_scene")
            or world_data.get("opening_scene")
            or scene.description
        )
        room_data = Room(
            room_id=str(data.get("room_id", "")),
            room_hash=str(data.get("room_hash", "")),
            phase=str(data.get("phase", "planning")),
            world=world,
            opening_scene=opening_scene,
            scene=scene,
            players=player_map,
            actions=cls._restore_actions(data.get("actions", {})),
            player_status=cls._restore_player_status(data.get("player_status", {})),
            timeline=[
                dict(event)
                for event in cls._dict_list(data.get("timeline", []))
            ],
            turn_index=turn_manager.turn_index,
            turn_history=list(context.turn_history),
            recent_summary=str(data.get("recent_summary", "")),
            next_player_id=cls._parse_int(
                data.get("next_player_id"),
                default=(max(player_map.keys(), default=0) + 1),
            ),
            host_player_id=host_player_id if host_player_id > 0 else None,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )
        for player_id in room_data.players:
            room_data.player_status.setdefault(player_id, False)

        room = cls(
            room_id=str(data.get("room_id", "")),
            phase=str(data.get("phase", "planning")),
            turn_manager=turn_manager,
            world=world,
            room=room_data,
        )
        return room

    def to_room_state(self) -> dict[str, Any]:
        self._sync_room_from_runtime()
        context = self.turn_manager.context_manager
        online_players = self.get_online_players()

        return {
            "room_id": self.room_id,
            "room_hash": self.room.room_hash,
            "created_at": self.room.created_at,
            "updated_at": self.room.updated_at,
            "host_player_id": self._format_player_id(self.room.host_player_id) if self.room.host_player_id else None,
            "turn_index": self.turn_manager.turn_index,
            "phase": self.phase,
            "world": {
                "title": self.world.title,
                "setting": self.world.setting,
                "opening_scene": self.room.opening_scene,
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
    def _calculate_room_hash(snapshot: Mapping[str, Any]) -> str:
        hash_source = {
            key: value
            for key, value in snapshot.items()
            if key != "room_hash"
        }
        payload = json.dumps(
            hash_source,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

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
