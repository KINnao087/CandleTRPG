from typing import Any, Dict, List

from backend.app.ai.gm_graph import build_gm_graph

_gm_graph = build_gm_graph()


def resolve_turn(
        *,
        world: str,
        scene: Dict[str, Any],
        characters: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        recent_summary: str = "",
) -> Dict[str, Any]:
    final_state = _gm_graph.invoke({
        "world": world,
        "scene": scene,
        "characters": characters,
        "player_actions": actions,
        "recent_summary": recent_summary,
    })

    return {
        "narration": final_state.get("narration", ""),
        "raw_state": final_state,
    }
