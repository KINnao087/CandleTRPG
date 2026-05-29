from typing import List

from backend.app.ai.gm_graph import build_gm_graph
from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene, TurnHistory, TurnResult, World
from backend.app.domain.room import PlayerInfo

_gm_graph = build_gm_graph()


def resolve_turn(
    *,
    world: str | World,
    scene: Scene,
    characters: List[PlayerInfo],
    actions: List[PlayerAction],
    history: List[TurnHistory] | None = None,
    host_note: str = "",
) -> TurnResult:
    if isinstance(world, World):
        world = f"{world.title}\n{world.setting}"

    final_state = _gm_graph.invoke({
        "world": world,
        "scene": scene,
        "characters": characters,
        "history": history or [],
        "player_actions": actions,
        "host_note": host_note,
    })

    return TurnResult.from_ai_state(final_state)
