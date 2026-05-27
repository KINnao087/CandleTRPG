# Frontend API Requirements

本文档列出当前 React 前端需要后端 FastAPI 提供的接口。

默认前端会请求同源接口。如果前后端分开端口运行，可以在 `frontend/.env` 中配置：

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 统一房间状态

多数接口建议直接返回完整房间状态，前端会用它刷新页面。

```json
{
  "room_id": "room_001",
  "turn_index": 1,
  "phase": "planning",
  "scene": {
    "time": "夜晚 21:30",
    "location": "MIX 酒馆",
    "description": "当前场景描述"
  },
  "players": [
    {
      "id": "player_001",
      "name": "林烛",
      "character_name": "林烛",
      "role": "player",
      "ready": false,
      "action_text": ""
    }
  ],
  "characters": [
    {
      "id": "char_001",
      "player_id": "player_001",
      "name": "林烛",
      "status": {
        "hp": 85,
        "conditions": []
      },
      "inventory": ["终端", "短刀", "急救喷雾"]
    }
  ],
  "timeline": [
    {
      "id": "event_001",
      "type": "scene",
      "title": "当前场景",
      "content": "线索集中在吧台后门与暗巷。",
      "timestamp": "21:30"
    }
  ]
}
```

`phase` 建议使用以下值：

```text
lobby
planning
locked
resolving
review
```

## REST API

### 获取房间状态

```http
GET /api/rooms/{room_id}/state
```

用途：页面打开、切换房间时读取当前房间。

响应：返回完整房间状态。

### 加入房间

```http
POST /api/rooms/{room_id}/join
```

请求体：

```json
{
  "player_name": "林烛",
  "character_name": "林烛",
  "role": "player"
}
```

`role` 可为：

```text
player
host
```

响应：

```json
{
  "player_id": "player_001",
  "room_state": {
    "room_id": "room_001"
  }
}
```

`room_state` 中建议返回完整房间状态。

### 提交行动

```http
POST /api/rooms/{room_id}/actions
```

请求体：

```json
{
  "player_id": "player_001",
  "character_name": "林烛",
  "action_text": "检查后门是否有脚印",
  "turn_index": 1
}
```

响应：返回完整房间状态。

### 更新准备状态

```http
POST /api/rooms/{room_id}/ready
```

请求体：

```json
{
  "player_id": "player_001",
  "ready": true
}
```

响应：返回完整房间状态。

### 房主结算回合

```http
POST /api/host/resolve-turn
```

请求体：

```json
{
  "room_id": "room_001",
  "host_note": "优先处理潜行失败风险",
  "force": false
}
```

字段说明：

- `room_id`：要结算的房间。
- `host_note`：房主给 AI 或结算逻辑的补充说明，可为空字符串。
- `force`：是否在未全员准备时强制结算。

响应：返回完整房间状态。结算成功后建议更新：

- `turn_index`
- `phase`
- `scene`
- `characters`
- `timeline`
- `players[].ready`
- `players[].action_text`

### 房主回滚

```http
POST /api/host/rollback
```

请求体：

```json
{
  "room_id": "room_001",
  "turn_index": 1
}
```

响应：返回完整房间状态。

## WebSocket API

### 房间连接

```text
WS /ws/rooms/{room_id}?player_id={player_id}
```

前端连接成功后会发送：

```json
{
  "type": "join_room",
  "room_id": "room_001",
  "player_id": "player_001",
  "payload": {},
  "timestamp": "2026-05-27T08:00:00.000Z"
}
```

### 服务端广播房间状态

```json
{
  "type": "room_state",
  "room_id": "room_001",
  "payload": {
    "room_id": "room_001"
  },
  "timestamp": "2026-05-27T08:00:00.000Z"
}
```

`payload` 建议返回完整房间状态。

### 服务端广播结算完成

```json
{
  "type": "turn_resolved",
  "room_id": "room_001",
  "payload": {
    "room_id": "room_001"
  },
  "timestamp": "2026-05-27T08:00:00.000Z"
}
```

`payload` 建议返回完整房间状态。

### 服务端返回错误

```json
{
  "type": "error",
  "room_id": "room_001",
  "payload": {
    "message": "错误说明"
  },
  "timestamp": "2026-05-27T08:00:00.000Z"
}
```

## FastAPI 实现建议

后端如果暂时不做数据库，可以先使用内存字典保存房间：

```python
rooms: dict[str, dict] = {}
```

最小可用流程：

1. `GET /api/rooms/{room_id}/state`：没有房间就创建默认房间并返回。
2. `POST /api/rooms/{room_id}/join`：创建或更新玩家，返回 `player_id` 和 `room_state`。
3. `POST /api/rooms/{room_id}/actions`：保存玩家行动。
4. `POST /api/rooms/{room_id}/ready`：更新玩家准备状态。
5. `POST /api/host/resolve-turn`：读取所有行动，调用现有 AI 结算逻辑，写入 `timeline`，推进回合。
6. `POST /api/host/rollback`：先可以只回滚 `turn_index` 和 `phase`，后续再接快照。
7. WebSocket：每次 REST 修改房间后，向该房间所有连接广播 `room_state`。
