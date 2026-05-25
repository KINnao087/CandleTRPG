# API 与消息协议草案

本文件记录设计文档中规划的 REST 接口与 WebSocket 消息类型，后续实现时应以实际代码为准同步更新。

## REST 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/` | 返回前端页面 |
| `POST` | `/api/campaigns` | 创建战役 |
| `GET` | `/api/campaigns/{id}` | 读取战役信息 |
| `POST` | `/api/campaigns/{id}/load` | 加载战役存档 |
| `POST` | `/api/campaigns/{id}/export` | 导出战役存档 |
| `GET` | `/api/rooms/{room_id}/state` | 获取房间当前状态 |
| `POST` | `/api/host/resolve-turn` | 房主请求结算当前回合 |
| `POST` | `/api/host/rollback` | 房主回滚到指定回合 |

## WebSocket 消息格式

```json
{
  "type": "action_submit",
  "room_id": "room_001",
  "player_id": "player_001",
  "payload": {
    "turn_index": 12,
    "action_text": "我检查后门有没有脚印。"
  },
  "timestamp": "2026-05-25T20:30:00"
}
```

## 常用消息类型

| 类型 | 方向 | 说明 |
| --- | --- | --- |
| `join_room` | 客户端 -> 服务端 | 玩家加入房间 |
| `room_state` | 服务端 -> 客户端 | 同步玩家列表、当前回合、阶段和场景 |
| `chat_message` | 双向 | 普通聊天或场外交流 |
| `action_submit` | 客户端 -> 服务端 | 提交或修改本轮行动 |
| `ready_update` | 双向 | 更新准备状态 |
| `turn_resolve_start` | 服务端 -> 客户端 | 通知进入 AI 结算阶段 |
| `turn_resolved` | 服务端 -> 客户端 | 广播 AI 结算后的剧情与状态更新 |
| `host_patch` | 房主 -> 服务端 | 房主修正剧情或状态 |
| `error` | 服务端 -> 客户端 | 错误信息 |
