# Frontend API Requirements

本文档列出当前 React 前端需要后端 FastAPI 提供的接口。

前端默认读取：

```env
VITE_API_BASE_URL=http://127.0.0.1:8001
```

当前页面流程：

1. 主菜单：输入用户名、角色名、房间 ID。
2. 查找并加入：直接加入已有房间。
3. 创建房间：进入房间创建菜单。
4. 房间创建菜单：创建者自动成为房主，导入或填写世界设定。
5. 创建并进入游戏：后端创建房间、保存世界设定、房主加入房间，然后进入正式跑团页面。

## 统一房间状态

多数接口建议返回完整房间状态，前端会用它刷新页面。

```json
{
  "room_id": "room_001",
  "turn_index": 1,
  "phase": "planning",
  "world": {
    "title": "霓虹旧城",
    "setting": "近未来都市旧城区被企业、帮派和地下情报贩子共同控制。"
  },
  "scene": {
    "time": "夜晚 21:30",
    "location": "MIX 酒馆",
    "description": "当前场景描述"
  },
  "players": [
    {
      "id": "player_001",
      "name": "张三",
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

`phase` 建议使用：

```text
lobby
planning
locked
resolving
review
```

## REST API

### 创建房间

```http
POST /api/rooms/{room_id}
```

用途：房主在创建菜单提交世界设定时调用。创建者应自动成为房主，但前端随后仍会调用 `join` 以拿到 `player_id`。

请求体：

```json
{
  "host_name": "张三",
  "character_name": "林烛",
  "world": {
    "title": "霓虹旧城",
    "setting": "近未来都市旧城区被企业、帮派和地下情报贩子共同控制。",
    "opening_scene": "玩家们在 MIX 酒馆后门前集合。"
  }
}
```

响应建议：

```json
{
  "room_state": {
    "room_id": "room_001"
  }
}
```

`room_state` 建议返回完整房间状态。

### 导入或更新世界设定

```http
POST /api/rooms/{room_id}/world
```

用途：保存创建菜单里导入或填写的世界设定。前端会在创建房间时调用一次。

请求体：

```json
{
  "title": "霓虹旧城",
  "setting": "完整世界设定文本，可以来自 .txt、.md 或 .json 文件。",
  "opening_scene": "玩家进入游戏后看到的第一幕。"
}
```

响应建议：

```json
{
  "room_state": {
    "room_id": "room_001"
  }
}
```

后端应将：

- `title` 保存到 `room_state.world.title`
- `setting` 保存到 AI 上下文里的世界设定
- `opening_scene` 用于初始化 `room_state.scene.description`

### 获取房间状态

```http
GET /api/rooms/{room_id}/state
```

用途：加入房间前检查房间、进入房间后刷新状态。

响应：返回完整房间状态。

### 加入房间

```http
POST /api/rooms/{room_id}/join
```

用途：玩家加入已有房间，或房主创建房间后加入并获取 `player_id`。

请求体：

```json
{
  "player_name": "张三",
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

`room_state` 建议返回完整房间状态。

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

如果暂时不做数据库，可以先使用内存字典保存房间：

```python
rooms: dict[str, dict] = {}
```

最小可用流程：

1. `POST /api/rooms/{room_id}`：创建房间，写入 `world` 和初始 `scene`。
2. `POST /api/rooms/{room_id}/world`：保存或更新世界设定，刷新 AI 上下文。
3. `GET /api/rooms/{room_id}/state`：读取房间状态。建议不存在时返回 `404`，避免“查找房间”误创建。
4. `POST /api/rooms/{room_id}/join`：创建或更新玩家，返回 `player_id` 和 `room_state`。
5. `POST /api/rooms/{room_id}/actions`：保存玩家行动。
6. `POST /api/rooms/{room_id}/ready`：更新玩家准备状态。
7. `POST /api/host/resolve-turn`：读取世界设定、当前场景、角色状态和玩家行动，调用 AI 结算，写入 `timeline`，推进回合。
8. `POST /api/host/rollback`：按 `turn_index` 恢复快照。
9. WebSocket：每次 REST 修改房间后，向该房间所有连接广播 `room_state`。
