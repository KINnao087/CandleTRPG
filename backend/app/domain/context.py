from dataclasses import dataclass, field
from typing import Any, List, Mapping

from backend.app.domain.action import PlayerAction


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
