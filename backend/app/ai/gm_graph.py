import json
from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.ai.llm_client import get_llm
from backend.app.domain.action import PlayerAction
from backend.app.domain.context import TurnHistory, TurnResult
from backend.app.domain.room import PlayerInfo


class GMState(TypedDict, total=False):
    world: str
    scene: Dict[str, Any]
    characters: List[PlayerInfo]
    history: List[TurnHistory]
    player_actions: List[PlayerAction]
    host_note: str
    prompt: str
    raw_response: str
    narration: str
    scene_update: Dict[str, Any]
    character_updates: List[Dict[str, Any]]


# 要想改数据的提示词请到domain
def _format_actions(actions: List[PlayerAction]) -> str:
    if not actions:
        return "无。"

    return "\n".join(f"- {action}" for action in actions)


def _format_characters(characters: List[PlayerInfo]) -> str:
    if not characters:
        return "暂无角色状态。"

    return "\n".join(f"- {character}" for character in characters)


def _format_history(history: List[TurnHistory]) -> str:
    if not history:
        return "暂无历史回合。"

    return "\n\n".join(str(turn) for turn in history)


def _output_rules() -> str:
    return """
【输出格式规则】
你必须只输出一个合法 JSON 对象，不要输出 Markdown，不要输出代码块，不要在 JSON 前后添加解释文字。

JSON 必须符合以下结构：
例子：
{
  "narration": "给玩家看的旁白",
  "scene_update": {
    "time": "当前时间",
    "location": "当前地点",
    "description": "下一回合要使用的客观场景描述"
  },
  "character_updates": [
    {
      "character_id": "char_001",
      "player_id": "player_001",
      "character_name": "林烛",
      "status_delta": {
        "hp": -13,
        "conditions_add": ["流血"],
        "conditions_remove": ["流血"]
      },
      "inventory_add": ["门禁卡"],
      "inventory_remove": ["急救喷雾"],
      "abilities": [
        {
          "name": "绯红之王",
          "description": "近距离力量型替身。",
          "sub_abilities": [
            {
              "name": "时间删除",
              "description": "可以删除最长为11秒的时间"
            },
            {
              "name": "预知未来",
              "description": "可以预知未来11秒的事件"
            }
          ]
        }
      ]
    }
  ]
}

字段要求：
1. narration 必须是玩家可见文本，用来展示本回合行动结果和环境变化。
2. scene_update.time 必须是本回合结束后的时间，不允许原样照抄当前时间，除非本回合行动几乎不消耗时间。AI 需要根据当前时间、玩家行动耗时和环境变化合理推算。
3. scene_update.location 必须给出本回合结束后的地点。如果地点没有变化，可以沿用当前地点。
4. scene_update.description 必须是客观场景状态，不要写成文学旁白；它会作为下一回合的当前场景。
5. scene_update.description 必须包含本回合已经确定的线索、位置、可见风险或环境变化。
6. 不要把玩家尚未选择的行动写进 scene_update。
7. 只有当角色能力在本回合明确发生变化时，才在对应 character_updates 项中返回 abilities 字段；否则不要返回 abilities 字段。
8. abilities 表示该角色变化后的完整能力列表，不是增量。
9. abilities 中如果某个能力包含多个可独立使用的效果，必须拆分到 sub_abilities 中。
10. ability.description 只描述该能力的总体性质、来源或共同限制；具体可使用效果写入 sub_abilities。
11. 例如“时间领主能够暂停、加速、倒退时间”必须写成：
  {
    "name": "时间领主",
    "description": "操纵时间流向的高阶能力，具体效果受体力、专注和场景限制。",
    "sub_abilities": [
      {
        "name": "时间暂停",
        "description": "短时间暂停周围时间。"
      },
      {
        "name": "时间加速",
        "description": "加快目标或局部区域的时间流速。"
      },
      {
        "name": "时间倒退",
        "description": "让目标或局部状态回退到短时间前。"
      }
    ]
  }
12. 单一效果时可以不写 sub_abilities 或写空数组。例如夜视，水下呼吸
13. 一般来说，玩家的ability是不会凭空消失的。除非故事中明确说明某种事件剥夺了玩家的ability
""".strip()


def build_prompt(state: GMState) -> dict[str, Any]:
    """根据上下文和玩家行动构造本回合 GM 提示词。"""
    world = state.get("world", "").strip()
    scene = state.get("scene", {})
    characters = state.get("characters", [])
    history = state.get("history", [])
    player_actions = state.get("player_actions", [])
    host_note = state.get("host_note", "").strip()

    scene_time = scene.get("time", "未知时间")
    scene_location = scene.get("location", "未知地点")
    scene_description = scene.get("description", "")

    prompt = f"""
你是一个多人跑团的 AI 主持人。你必须优先结算【本轮玩家行动】，然后补充环境变化。

【本轮玩家行动】
{_format_actions(player_actions)}

【房主补充说明】
{host_note or "无。"}

【强制要求】
1. 必须逐条回应本轮玩家行动，并给出直接结果。
2. 不要描写任何与玩家行动矛盾的位置、状态或行为。
3. 不要替玩家做关键选择，不要擅自让玩家角色说出关键台词。
4. 只推进当前行动造成的直接结果，不要一次推进太多剧情。
5. 保持场景连续，不要突然切换地点、时间或新增重大设定。
6. 历史回合只能作为上下文参考，本轮输出必须服务于本轮玩家行动。
7. 房主的补充是高于一切的。
    例如：如果房主补充了“现在某某玩家直接爆炸”，那个玩家会立刻爆炸
        如果房主补充了面前出现黑洞，那么面前就会出现黑洞。
        也就是说，房主的补充就是上帝的补充

【世界设定】
{world}

【当前客观场景】
时间：{scene_time}
地点：{scene_location}
描述：{scene_description}

【角色状态】
{_format_characters(characters)}
【角色状态更新规范】
0. 最重要的一点。host可以改变任意角色的状态。你需要根据is_host的值来判断此角色是否事host
1. 如果角色物品栏满了，意味着角色无法拾取新的东西，玩家任何试图拾起物品的行为都应当失效
2. 如果角色血量见底，角色死亡。在此次跑团中无法再做出任何行动。除非使用某种方式复活
3. 角色如果做出超出他能力范围的事，一律不予通过。
    例如：一个只会时停的角色尝试时间加速。
同时，如果过于夸张也不予通过，除非角色成长到夸张的阶段。
    例如：一个会飞行的角色尝试超光速飞行。
4. 角色如果想成长，必须结合他的资源来判断是否能成长。禁止角色凭空领悟出一个能力。
    例如：一个角色会飞行。如果他要求“我现在领悟了时停”，不予以通过，除非故事中主动赋予了他

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
            "character_updates": [],
        }

    llm = get_llm()
    response = llm.invoke(prompt)
    raw_response = response.content

    return {
        "raw_response": raw_response,
    }

def parse_llm_output(state: GMState) -> dict[str, Any]:
    parsed = json.loads(state["raw_response"])

    scene_update = parsed.get("scene_update", {})
    return {
        "narration": parsed.get("narration", ""),
        "scene_update": {
            "time": scene_update.get("time", ""),
            "location": scene_update.get("location", ""),
            "description": scene_update.get("description", ""),
        },
        "character_updates": TurnResult.extract_character_updates(parsed),
    }


def build_gm_graph():
    graph = StateGraph(GMState)

    graph.add_node("build_prompt", build_prompt)
    graph.add_node("call_llm", call_llm)
    graph.add_node("parse_llm_output", parse_llm_output)

    graph.add_edge(START, "build_prompt")
    graph.add_edge("build_prompt", "call_llm")
    graph.add_edge("call_llm", "parse_llm_output")
    graph.add_edge("parse_llm_output", END)

    return graph.compile()
