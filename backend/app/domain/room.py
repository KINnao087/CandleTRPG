from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from backend.app.domain.action import PlayerAction
from backend.app.domain.context import Scene, TurnHistory, World


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class SubAbilities:
    name: str
    description: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SubAbilities":
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
        }

    def __str__(self) -> str:
        return (
            f"name={self.name}; "
            f"description={self.description}"
        )


@dataclass
class Abilities:
    name: str
    description: str
    sub_abilities: list[SubAbilities] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Abilities":
        sub_abilities = data.get("sub_abilities", data.get("subAbilities", []))
        if not isinstance(sub_abilities, list):
            sub_abilities = []

        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            sub_abilities=[
                SubAbilities.from_dict(sub_ability)
                for sub_ability in sub_abilities
                if isinstance(sub_ability, dict)
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "sub_abilities": [
                sub_ability.to_dict()
                for sub_ability in self.sub_abilities
            ],
        }

    def __str__(self) -> str:
        sub_abilities_text = ", ".join(
            str(sub_ability)
            for sub_ability in self.sub_abilities
        ) or "none"

        return (
            f"name={self.name}; "
            f"description={self.description}; "
            f"sub_abilities={sub_abilities_text}; "
        )


@dataclass
class PlayerInfo:
    id: int
    name: str
    character_name: str
    inventory: list[str] = field(default_factory=list)
    inventory_limits: int = 5
    status: dict[str, Any] = field(default_factory=lambda: {
        "hp": 100,
        "conditions": [],
    })
    abilities: list[Abilities] = field(default_factory=list)
    is_online: bool = True
    is_host: bool = False

    def apply_update(self, update: dict[str, Any]) -> None:
        for key, value in update.items():
            handler = getattr(self, f"_apply_{key}", None)
            if handler is not None:
                handler(value)

    def _apply_status(self, value: dict[str, Any]) -> None:
        if isinstance(value, dict):
            self.status = {
                **self.status,
                **value,
            }

    def _apply_status_delta(self, value: dict[str, Any]) -> None:
        if not isinstance(value, dict):
            return

        for key, delta in value.items():
            handler = getattr(self, f"_apply_status_delta_{key}", None)
            if handler is not None:
                handler(delta)
                continue

            current_value = self.status.get(key)
            if isinstance(current_value, (int, float)) and isinstance(delta, (int, float)):
                next_value = current_value + delta
                self.status[key] = max(0, next_value) if key == "hp" else next_value
            else:
                self.status[key] = delta

    def _apply_status_delta_conditions_add(self, value: list[str]) -> None:
        if not isinstance(value, list):
            return

        conditions = list(self.status.get("conditions", []))
        for condition in value:
            if condition not in conditions:
                conditions.append(condition)
        self.status["conditions"] = conditions

    def _apply_status_delta_conditions_remove(self, value: list[str]) -> None:
        if not isinstance(value, list):
            return

        conditions = list(self.status.get("conditions", []))
        self.status["conditions"] = [
            condition for condition in conditions
            if condition not in value
        ]

    def _apply_inventory(self, value: list[str]) -> None:
        if isinstance(value, list):
            self.inventory = list(value)

    def _apply_inventory_add(self, value: list[str]) -> None:
        if not isinstance(value, list):
            return

        #允许重复
        for item in value:
            self.inventory.append(item)

    def _apply_inventory_remove(self, value: list[str]) -> None:
        if not isinstance(value, list):
            return

        for item in value:
            for item in self.inventory:
                self.inventory.remove(item)

    def _apply_abilities(self, value: list[dict[str, Any]]) -> None:
        if not isinstance(value, list):
            return

        self.abilities = [
            Abilities.from_dict(ability)
            for ability in value
            if isinstance(ability, dict)
        ]

    def __str__(self) -> str:
        abilities_text = ", ".join(str(ability) for ability in self.abilities) or "无"
        return (
            f"character_id={self.character_id}; "
            f"player_id={self.player_id}; "
            f"character_name={self.character_name}; "
            f"status={self.status}; "
            f"inventory={self.inventory}; "
            f"inventory_limits={self.inventory_limits}; "
            f"abilities={abilities_text}; "
            f"is_online={self.is_online}; "
            f"is_host={self.is_host}"
        )

    @property
    def player_id(self) -> str:
        return f"player_{self.id:03d}"

    @property
    def character_id(self) -> str:
        return f"char_{self.id:03d}"


@dataclass
class Room:
    room_id: str
    phase: str
    world: World
    opening_scene: str
    scene: Scene
    players: dict[int, PlayerInfo] = field(default_factory=dict)
    actions: dict[int, PlayerAction] = field(default_factory=dict)
    player_status: dict[int, bool] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    turn_index: int = 1
    turn_history: list[TurnHistory] = field(default_factory=list)
    recent_summary: str = ""
    next_player_id: int = 1
    host_player_id: int | None = None
    room_hash: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    @property
    def host(self) -> PlayerInfo | None:
        if self.host_player_id is not None:
            host = self.players.get(self.host_player_id)
            if host is not None:
                return host

        for player in self.players.values():
            if player.is_host:
                return player

        return None
