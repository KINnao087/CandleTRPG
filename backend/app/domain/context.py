from dataclasses import dataclass, field
from typing import Any, List, Mapping

from pydantic import BaseModel, ConfigDict, Field

from backend.app.domain.action import PlayerAction


class GMSubAbilityOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="子能力名称")
    description: str = Field(description="子能力的具体效果")


class GMAbilityOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="能力名称")
    description: str = Field(description="能力的总体性质、来源或共同限制")
    sub_abilities: list[GMSubAbilityOutput] = Field(
        default_factory=list,
        description="该能力包含的可独立使用效果",
    )


class GMStatusDeltaOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hp: int | None = Field(
        default=None,
        description="生命值变化量；受到伤害时为负数，恢复生命时为正数",
    )
    conditions_add: list[str] = Field(
        default_factory=list,
        description="本回合新增的角色状态",
    )
    conditions_remove: list[str] = Field(
        default_factory=list,
        description="本回合移除的角色状态",
    )


class GMCharacterUpdateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character_id: str = Field(description="角色 ID，例如 char_001")
    player_id: str = Field(description="玩家 ID，例如 player_001")
    character_name: str = Field(description="角色名称")
    status_delta: GMStatusDeltaOutput | None = Field(
        default=None,
        description="角色状态的增量变化；没有状态变化时省略",
    )
    inventory_add: list[str] = Field(
        default_factory=list,
        description="本回合加入角色物品栏的物品",
    )
    inventory_remove: list[str] = Field(
        default_factory=list,
        description="本回合从角色物品栏移除的物品",
    )
    abilities: list[GMAbilityOutput] | None = Field(
        default=None,
        description=(
            "仅在能力发生变化时返回，内容是变化后的完整能力列表；"
            "没有变化时必须省略"
        ),
    )


class GMSceneUpdateOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    time: str = Field(description="本回合结束后的时间")
    location: str = Field(description="本回合结束后的地点")
    description: str = Field(
        description="供下一回合使用的客观场景状态，不是文学旁白",
    )


class GMTurnOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    narration: str = Field(
        description="向玩家展示的本回合行动结果和环境变化",
    )
    scene_update: GMSceneUpdateOutput
    character_updates: list[GMCharacterUpdateOutput] = Field(
        default_factory=list,
        description="本回合发生变化的角色；没有角色变化时返回空列表",
    )


@dataclass
class World:
    title: str
    setting: str

class Scene(dict):
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Scene":
        return cls(
            time=str(data.get("time", "")),
            location=str(data.get("location", "")),
            description=str(data.get("description", "")),
        )

    def __init__(self, *, time: str = "", location: str = "", description: str = ""):
        super().__init__(
            time=time,
            location=location,
            description=description,
        )

    @property
    def time(self) -> str:
        return self.get("time", "")

    @property
    def location(self) -> str:
        return self.get("location", "")

    @property
    def description(self) -> str:
        return self.get("description", "")


@dataclass
class TurnHistory:
    turn_index: int
    actions: List[PlayerAction]
    narration: str
    scene: Scene
    character_updates: List[dict[str, Any]] = field(default_factory=list)

    def __str__(self) -> str:
        actions_text = "\n".join(f"- {action}" for action in self.actions) or "无。"
        return (
            f"第 {self.turn_index} 回合\n"
            f"玩家行动：\n{actions_text}\n"
            f"主持人结果：\n{self.narration}\n"
            f"回合结束场景：time={self.scene.time}; "
            f"location={self.scene.location}; "
            f"description={self.scene.description}"
        )


@dataclass
class TurnResult:
    narration: str
    scene: Scene
    character_updates: List[dict[str, Any]] = field(default_factory=list)
    raw_state: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_ai_state(cls, state: Mapping[str, Any]) -> "TurnResult":
        return cls(
            narration=str(state.get("narration", "")),
            scene=Scene.from_dict(state.get("scene_update", {})),
            character_updates=cls.extract_character_updates(state),
            raw_state=dict(state),
        )

    @staticmethod
    def extract_character_updates(data: Mapping[str, Any]) -> List[dict[str, Any]]:
        return TurnResult._extract_dict_list(data.get("character_updates", []))

    @staticmethod
    def _extract_dict_list(value: Any) -> List[dict[str, Any]]:
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return []
