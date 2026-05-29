from typing import Any, Dict, List

from backend.app.ai.gm_graph import build_gm_graph
from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene, World
from backend.app.domain.room import PlayerInfo

_gm_graph = build_gm_graph()


def resolve_turn(
    *,
    world: str | World,
    scene: Scene,
    characters: List[PlayerInfo],
    actions: List[PlayerAction],
    history: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if isinstance(world, World):
        world = f"{world.title}\n{world.setting}"

    final_state = _gm_graph.invoke({
        "world": world,
        "scene": scene,
        "characters": characters,
        "history": history or [],
        "player_actions": actions,
    })

    return {
        "narration": final_state.get("narration", ""),
        "scene": Scene.from_dict(final_state.get("scene_update", {})),
        "character_updates": final_state.get("character_updates", []),
        "raw_state": final_state,
    }
