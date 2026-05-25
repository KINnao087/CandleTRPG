from typing import Any, Dict, List

from backend.app.ai.gm_graph import build_gm_graph
from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene

_gm_graph = build_gm_graph()


def resolve_turn(
    *,
    world: str,
    scene: Scene,
    characters: List[Dict[str, Any]],
    actions: List[PlayerAction],
    history: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
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
        "raw_state": final_state,
    }
