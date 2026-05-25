# CandleTRPG-LAN 设计文档索引

本目录用于存放从设计书拆分出的工程文档。

当前完整设计来源为根目录的 `CandleTRPG_LAN_System_Design.docx`，其核心结论如下：

- 架构采用浏览器客户端 + Python FastAPI 服务端。
- 服务端负责房间管理、回合管理、WebSocket 同步、AI 主持流程和本地存档。
- 前端负责剧情展示、行动提交、准备状态、角色状态和房主控制台。
- 存储建议采用 SQLite + JSONL：SQLite 存结构化状态，JSONL 存事件日志。
- MVP 主链路为“多人输入 -> AI 结算 -> 状态同步 -> 存档保存”。

后续可将原始设计书逐步拆分为：

- `architecture.md`
- `data_model.md`
- `ai_agent.md`
- `storage.md`
- `test_plan.md`
