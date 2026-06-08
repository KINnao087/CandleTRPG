from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from backend.app.ai.prompts.gm_rules import SYSTEM_RULES

GM_TURN_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessage(content=SYSTEM_RULES),
    ("human",
     """
【本轮玩家行动】
{player_actions}

【房主补充说明】
{host_note}

【世界设定】
{world}

【当前客观场景】
时间：{scene_time}
地点：{scene_location}
描述：{scene_description}

【角色状态】
{characters}

【历史回合】
{history}
""".strip(),
     ),
])
