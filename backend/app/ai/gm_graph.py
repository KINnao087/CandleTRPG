from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.ai import get_llm


class PlayerAction(TypedDict):
    player_id: str
    character_name: str
    action_text: str


class GMState(TypedDict, total=False):
    world: str
    scene: Dict[str, Any]
    player_actions: List[PlayerAction]
    narration: str
    prompt: str


def build_prompt(state: GMState) -> dict[str, Any]:
    """根据世界设定、当前场景和玩家行动构造本回合 GM 提示词。"""
    world = state.get("world", "").strip()
    scene = state.get("scene", {})
    player_actions = state.get("player_actions", [])

    scene_time = scene.get("time", "未知时间")
    scene_location = scene.get("location", "未知地点")
    scene_description = scene.get("description", "")

    actions_text = "\n".join(
        f"- {action.get('character_name', '未知角色')}：{action.get('action_text', '')}"
        for action in player_actions
    )

    prompt = f"""
你是一个多人跑团的 AI 主持人。你必须优先结算【本轮玩家行动】，然后补充环境变化。

【本轮玩家行动】
{actions_text}

【强制要求】
1. 必须逐条回应本轮玩家行动，并给出直接结果。
2. 不要描写任何与玩家行动矛盾的位置、状态或行为。
3. 不要替玩家做关键选择，不要擅自让玩家角色说出关键台词。
4. 只推进当前行动造成的直接结果，不要一次推进太多剧情。
5. 保持场景连续，不要突然切换地点、时间或新增重大设定。
6. 不要输出代码块，不要输出 JSON。

【世界设定】
{world}

【当前客观场景】
时间：{scene_time}
地点：{scene_location}
描述：{scene_description}

请严格按以下结构输出：
行动结果：
...
环境变化：
...
下一步可行动空间：
...
""".strip()

    return {
        "prompt": prompt,
    }


def call_llm(state: GMState) -> dict[str, Any]:
    """调用大模型，根据 prompt 生成本回合旁白。"""
    prompt = state.get("prompt", "").strip()

    if not prompt:
        return {
            "narration": "【系统错误】prompt 为空，无法生成剧情。",
        }

    llm = get_llm()
    response = llm.invoke(prompt)

    return {
        "narration": response.content,
    }


def build_gm_graph():
    graph = StateGraph(GMState)

    graph.add_node("build_prompt", build_prompt)
    graph.add_node("call_llm", call_llm)

    graph.add_edge(START, "build_prompt")
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", END)

    return graph.compile()
