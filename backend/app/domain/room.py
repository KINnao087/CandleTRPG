from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlayerInfo:
    id: int
    name: str
    character_name: str
    inventory: list[str] = field(default_factory=list)
    status: dict[str, Any] = field(default_factory=lambda: {
        "hp": 100,
        "conditions": [],
    })
    is_host: bool = False
