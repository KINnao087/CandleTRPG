from typing import Any, List, Mapping, TypedDict

from backend.app.domain.action import PlayerAction


class TurnHistory(TypedDict):
    turn_index: int
    actions: List[PlayerAction]
    narration: str
    scene: str

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
