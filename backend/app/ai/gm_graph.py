import json
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.ai.llm_client import get_llm
from backend.app.domain.action import PlayerAction
from backend.app.domain.context import TurnHistory


class GMState(TypedDict, total=False):
    world: str
    scene: Dict[str, Any]
    characters: List[Dict[str, Any]]
    history: List[TurnHistory]
    player_actions: List[PlayerAction]
    prompt: str
    raw_response: str
    narration: str
    scene_update: Dict[str, Any]


def _format_actions(actions: List[PlayerAction]) -> str:
    if not actions:
        return "无。"

    return "\n".join(
        f"- {action.get('character_name', '未知角色')}：{action.get('action_text', '')}"
        for action in actions
    )


def _format_characters(characters: List[Dict[str, Any]]) -> str:
    if not characters:
        return "暂无角色状态。"

    return "\n".join(
        f"- {character.get('name', '未知角色')}："
        f"状态={character.get('status', {})}；"
        f"物品={character.get('inventory', [])}"
        for character in characters
    )


def _format_history(history: List[TurnHistory]) -> str:
    if not history:
        return "暂无历史回合。"

    blocks = []
    for turn in history:
        blocks.append(
            f"第 {turn.get('turn_index', '未知')} 回合\n"
            f"玩家行动：\n{_format_actions(turn.get('actions', []))}\n"
            f"主持人结果：\n{turn.get('narration', '')}"
        )

    return "\n\n".join(blocks)


def _output_rules() -> str:
    return """
【输出格式规则】
你必须只输出一个合法 JSON 对象，不要输出 Markdown，不要输出代码块，不要在 JSON 前后添加解释文字。

JSON 必须符合以下结构：
{
  "narration": "给玩家看的旁白",
  "scene_update": {
    "time": "当前时间",
    "location": "当前地点",
    "description": "下一回合要使用的客观场景描述"
  }
}

字段要求：
1. narration 必须是玩家可见文本，用来展示本回合行动结果和环境变化。
2. scene_update.time 必须是本回合结束后的时间，不允许原样照抄当前时间，除非本回合行动几乎不消耗时间。AI 需要根据当前时间、玩家行动耗时和环境变化合理推算。
3. scene_update.location 必须给出本回合结束后的地点。如果地点没有变化，可以沿用当前地点。
4. scene_update.description 必须是客观场景状态，不要写成文学旁白；它会作为下一回合的当前场景。
5. scene_update.description 必须包含本回合已经确定的线索、位置、可见风险或环境变化。
6. 不要把玩家尚未选择的行动写进 scene_update。
""".strip()


def build_prompt(state: GMState) -> dict[str, Any]:
    """根据上下文和玩家行动构造本回合 GM 提示词。"""
    world = state.get("world", "").strip()
    scene = state.get("scene", {})
    characters = state.get("characters", [])
    history = state.get("history", [])
    player_actions = state.get("player_actions", [])

    scene_time = scene.get("time", "未知时间")
    scene_location = scene.get("location", "未知地点")
    scene_description = scene.get("description", "")

    prompt = f"""
你是一个多人跑团的 AI 主持人。你必须优先结算【本轮玩家行动】，然后补充环境变化。

【本轮玩家行动】
{_format_actions(player_actions)}

【强制要求】
1. 必须逐条回应本轮玩家行动，并给出直接结果。
2. 不要描写任何与玩家行动矛盾的位置、状态或行为。
3. 不要替玩家做关键选择，不要擅自让玩家角色说出关键台词。
4. 只推进当前行动造成的直接结果，不要一次推进太多剧情。
5. 保持场景连续，不要突然切换地点、时间或新增重大设定。
6. 历史回合只能作为上下文参考，本轮输出必须服务于本轮玩家行动。

【世界设定】
{world}

【当前客观场景】
时间：{scene_time}
地点：{scene_location}
描述：{scene_description}

【角色状态】
{_format_characters(characters)}

【历史回合】
{_format_history(history)}
历史回合的结构是玩家当前回合的动作+当前回合行动后的结果

{_output_rules()}
""".strip()

    return {"prompt": prompt}


def call_llm(state: GMState) -> dict[str, Any]:
    """调用大模型，根据 prompt 生成本回合结果。"""
    prompt = state.get("prompt", "").strip()

    if not prompt:
        return {
            "raw_response": "",
            "narration": "【系统错误】prompt 为空，无法生成剧情。",
            "scene_update": {},
        }

    llm = get_llm()
    response = llm.invoke(prompt)
    raw_response = response.content
    parsed = json.loads(raw_response)
    scene_update = parsed.get("scene_update", {})

    return {
        "raw_response": raw_response,
        "narration": parsed.get("narration", ""),
        "scene_update": {
            "time": scene_update.get("time", ""),
            "location": scene_update.get("location", ""),
            "description": scene_update.get("description", ""),
        },
    }


def build_gm_graph():
    graph = StateGraph(GMState)

    graph.add_node("build_prompt", build_prompt)
    graph.add_node("call_llm", call_llm)

    graph.add_edge(START, "build_prompt")
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", END)

    return graph.compile()
