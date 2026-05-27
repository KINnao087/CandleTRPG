from dataclasses import dataclass


@dataclass
class PlayerInfo:
    id: int
    name: str
    character_name: str
    is_host: bool = False
