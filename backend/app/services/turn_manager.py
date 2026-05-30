from typing import List

from backend.app.ai import resolve_turn
from backend.app.domain.action import PlayerAction
from backend.app.domain.room import PlayerInfo
from backend.app.services.context_manager import ContextManager


class TurnManager:
    def __init__(self, context_manager: ContextManager):
        self.context_manager = context_manager
        self.turn_index = 1

    def resolve_turn(
        self,
        actions: List[PlayerAction],
        host_note: str = "",
        active_characters: List[PlayerInfo] | None = None,
    ):
        ai_context = self.context_manager.build_ai_context()

        result = resolve_turn(
            world=ai_context["world"],
            scene=ai_context["scene"],
            characters=active_characters if active_characters is not None else ai_context["characters"],
            history=ai_context["history"],
            actions=actions,
            host_note=host_note,
        )

        self.context_manager.record_turn(
            turn_index=self.turn_index,
            actions=actions,
            result=result,
        )
        self.turn_index += 1
        return result
