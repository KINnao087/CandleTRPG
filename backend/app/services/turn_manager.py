from typing import List

from backend.app.ai import resolve_turn
from backend.app.domain.action import PlayerAction
from backend.app.services.context_manager import ContextManager


class TurnManager:
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.turn_index = 1

    def resolve_turn(self, actions: List[PlayerAction]):
        ai_context = self.context_manager.build_ai_context()

        res = resolve_turn(
            world=ai_context["world"],
            scene=ai_context["scene"],
            characters=ai_context["characters"],
            history=ai_context["history"],
            actions=actions,
        )

        self.context_manager.record_turn(
            turn_index=self.turn_index,
            actions=actions,
            narration=res["narration"],
            scene=res["scene"],
        )
        self.turn_index += 1
        return res
