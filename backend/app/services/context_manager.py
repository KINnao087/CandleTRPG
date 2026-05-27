from typing import List, TypedDict

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import TurnHistory, Scene


class ContextManager:
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

    def record_turn(self, turn_index: int, actions: List[PlayerAction], narration: str, scene: Scene):
        self.turn_history.append({
            "turn_index": turn_index,
            "actions": actions,
            "narration": narration,
            "scene": scene,
        })

        self.update_scene(scene)