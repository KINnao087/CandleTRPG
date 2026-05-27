from pydantic import BaseModel


class WorldRequest(BaseModel):
    title: str
    setting: str
    opening_scene: str


class CreateRoomRequest(BaseModel):
    host_name: str
    character_name: str
    world: WorldRequest


class JoinRequest(BaseModel):
    player_name: str
    character_name: str
    role: str

class PlayerActionRequest(BaseModel):
    player_id: str
    character_name: str
    action_text: str
    turn_index: int

class PlayerReadyRequest(BaseModel):
    player_id: str
    ready: bool

class HostResolveRequest(BaseModel):
    room_id: str
    host_note: str
    force: bool #是否在未全员准备时强制结算

class HostRollBackRequest(BaseModel):
    room_id: str
    turn_index: int
