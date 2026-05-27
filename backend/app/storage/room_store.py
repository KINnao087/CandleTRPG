from typing import Any

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import World
from backend.app.domain.room import PlayerInfo
from backend.app.services.turn_manager import TurnManager


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
        self._next_player_id += 1

        self.players[player.id] = player
        self.player_status[player.id] = False
        return player

    def player_action(self, player_id: int, action: PlayerAction) -> None:
        self.actions[player_id] = action

    def change_player_status(self, player_id: int, status: bool) -> None:
        self.player_status[player_id] = status

    def try_resolve_turn(self) -> bool:
        for player_id in self.players:
            if not self.player_status.get(player_id, False):
                return False

        self.phase = "resolving"
        turn_index = self.turn_manager.turn_index
        result = self.turn_manager.resolve_turn(list(self.actions.values()))

        self.timeline.insert(0, {
            "id": f"event_{turn_index:03d}",
            "type": "turn_resolved",
            "title": f"第 {turn_index} 回合结算",
            "content": result.get("narration", ""),
            "timestamp": result.get("scene", {}).get("time", ""),
        })

        self.actions.clear()

        for player_id in self.player_status:
            self.player_status[player_id] = False

        self.phase = "planning"
        return True

    def to_room_state(self) -> dict[str, Any]:
        context = self.turn_manager.context_manager

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
                    "action_text": self.actions.get(player.id, {}).get("action_text", ""),
                }
                for player in self.players.values()
            ],
            "characters": self._format_characters(context.characters),
            "timeline": self.timeline,
        }

    @staticmethod
    def _format_player_id(player_id: int) -> str:
        return f"player_{player_id:03d}"

    @staticmethod
    def _format_characters(characters: list[Any]) -> list[dict[str, Any]]:
        result = []
        for index, character in enumerate(characters, start=1):
            if isinstance(character, dict):
                result.append(character)
            else:
                result.append({
                    "id": f"char_{index:03d}",
                    "player_id": f"player_{index:03d}",
                    "name": str(character),
                    "status": {
                        "hp": 100,
                        "conditions": [],
                    },
                    "inventory": [],
                })
        return result


class RoomStore:
    def __init__(self):
        self.rooms: dict[str, RoomRuntimeInfo] = {}

    def add_room(self, room: RoomRuntimeInfo) -> None:
        self.rooms[room.room_id] = room

    def get_room(self, room_id: str) -> RoomRuntimeInfo | None:
        return self.rooms.get(room_id)
