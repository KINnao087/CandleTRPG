from typing import Any, List, TypedDict

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import TurnHistory, Scene, World
from backend.app.domain.room import PlayerInfo


class ContextManager:
    world: World
    scene: Scene
    characters: List[PlayerInfo]
    turn_history: List[TurnHistory]

    def __init__(self, world, scene, characters):
        self.world = world
        self.scene = scene
        self.characters = characters
        self.turn_history: List[TurnHistory] = []
        self.recent_summary = ""

    def build_ai_context(self):
        return {
            "world": self.world,
            "scene": self.scene,
            "characters": self.characters,
            "history": self.turn_history,
        }

    def update_scene(self, scene: Scene):
        self.scene = scene

    def apply_character_updates(self, character_updates: list[dict[str, Any]] | None):
        for update in character_updates or []:
            character = self._find_character_for_update(update)
            if character is None:
                continue

            status = update.get("status")
            if isinstance(status, dict):
                character.status = {
                    **character.status,
                    **status,
                }

            status_delta = update.get("status_delta")
            if isinstance(status_delta, dict):
                self._apply_status_delta(character, status_delta)

            inventory = update.get("inventory")
            if isinstance(inventory, list):
                character.inventory = list(inventory)

            inventory_add = update.get("inventory_add")
            if isinstance(inventory_add, list):
                for item in inventory_add:
                    if item not in character.inventory:
                        character.inventory.append(item)

            inventory_remove = update.get("inventory_remove")
            if isinstance(inventory_remove, list):
                character.inventory = [
                    item for item in character.inventory
                    if item not in inventory_remove
                ]

    def _find_character_for_update(self, update: dict[str, Any]) -> PlayerInfo | None:
        character_id = self._parse_prefixed_id(update.get("character_id"), "char_")
        player_id = self._parse_prefixed_id(update.get("player_id"), "player_")
        character_name = update.get("character_name")

        if character_id is not None:
            for character in self.characters:
                if character.id == character_id:
                    return character

        if player_id is not None and character_name:
            for character in self.characters:
                if character.id == player_id and character.character_name == character_name:
                    return character

        if player_id is not None:
            for character in self.characters:
                if character.id == player_id:
                    return character

        if character_name:
            for character in self.characters:
                if character.character_name == character_name:
                    return character

        return None

    @staticmethod
    def _parse_prefixed_id(value: Any, prefix: str) -> int | None:
        if value is None:
            return None

        text = str(value)
        if text.startswith(prefix):
            text = text.removeprefix(prefix)

        try:
            return int(text)
        except ValueError:
            return None

    @staticmethod
    def _apply_status_delta(character: PlayerInfo, status_delta: dict[str, Any]):
        for key, value in status_delta.items():
            if key == "conditions_add" and isinstance(value, list):
                conditions = list(character.status.get("conditions", []))
                for condition in value:
                    if condition not in conditions:
                        conditions.append(condition)
                character.status["conditions"] = conditions
                continue

            if key == "conditions_remove" and isinstance(value, list):
                conditions = list(character.status.get("conditions", []))
                character.status["conditions"] = [
                    condition for condition in conditions
                    if condition not in value
                ]
                continue

            current_value = character.status.get(key)
            if isinstance(current_value, (int, float)) and isinstance(value, (int, float)):
                next_value = current_value + value
                character.status[key] = max(0, next_value) if key == "hp" else next_value
            else:
                character.status[key] = value

    def record_turn(
        self,
        turn_index: int,
        actions: List[PlayerAction],
        narration: str,
        scene: Scene,
        character_updates: list[dict[str, Any]] | None = None,
    ):
        self.turn_history.append({
            "turn_index": turn_index,
            "actions": actions,
            "narration": narration,
            "scene": scene,
            "character_updates": character_updates or [],
        })

        self.apply_character_updates(character_updates)
        self.update_scene(scene)
