from typing import Any, List

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import TurnHistory, TurnResult, Scene, World
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

            character.apply_update(update)

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

    def record_turn(
        self,
        turn_index: int,
        actions: List[PlayerAction],
        result: TurnResult,
    ):
        self.turn_history.append(
            TurnHistory(
                turn_index=turn_index,
                actions=actions,
                narration=result.narration,
                scene=result.scene,
                character_updates=result.character_updates,
            )
        )

        self.apply_character_updates(result.character_updates)
        self.update_scene(result.scene)
