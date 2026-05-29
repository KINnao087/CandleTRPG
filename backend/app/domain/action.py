from dataclasses import dataclass


@dataclass
class PlayerAction:
    player_id: str
    character_name: str
    action_text: str

    def __str__(self) -> str:
        return (
            f"player_id={self.player_id}; "
            f"character_name={self.character_name}; "
            f"action={self.action_text}"
        )
