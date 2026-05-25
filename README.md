# CandleTRPG-LAN

局域网多人 AI 跑团系统，项目代号“烛火跑团”。本项目面向 2-6 名玩家在同一局域网内通过浏览器加入同一个跑团房间，由服务端负责房间、回合、同步、存档与 AI 主持流程。

当前仓库处于设计落地阶段：已根据 `CandleTRPG_LAN_System_Design.docx` 补齐项目目录结构，尚未实现业务代码。

## 项目目标

- 房主在本机启动 Python 服务端，并在局域网内提供访问地址。
- 玩家通过浏览器加入房间，实时同步剧情、角色状态、准备状态和回合结果。
- 每轮由玩家同时提交行动，准备后锁定，房主触发 AI 统一结算。
- AI 输出剧情文本与结构化状态更新，房主可审核、修正、回滚。
- 每回合保存事件日志与状态快照，支持长期战役连续推进。

## 技术方向

- 后端：Python + FastAPI
- 实时通信：WebSocket
- 前端：React + Vite，MVP 也可先用原生页面验证
- 存储：SQLite + JSONL 事件日志
- AI 接入：抽象 `AIClient`，后续可适配 OpenAI API、本地 Ollama 或其他模型
- 部署：局域网本地运行，不默认依赖公网服务

## 目录结构

```text
.
├── backend/
│   ├── app/
│   │   ├── api/              # REST 接口：战役、房间、房主操作等
│   │   ├── ws/               # WebSocket 消息、连接管理与广播
│   │   ├── services/         # 应用服务：房间、回合、游戏流程编排
│   │   ├── domain/           # 核心领域对象：战役、角色、场景、回合、行动
│   │   ├── ai/               # AI 主持 Agent、Prompt、模型适配与输出解析
│   │   ├── storage/          # SQLite、JSONL、快照、导入导出
│   │   ├── rules/            # 规则插件、骰点、战斗、奖励等扩展逻辑
│   │   └── utils/            # 通用工具
│   ├── prompts/              # Prompt 模板
│   └── saves/                # 本地战役存档
├── frontend/
│   ├── public/               # 静态资源
│   └── src/
│       ├── pages/            # 页面：玩家页、房主页、加入页等
│       ├── components/       # UI 组件
│       ├── store/            # 前端状态管理
│       ├── websocket/        # WebSocket 客户端封装
│       └── assets/           # 前端资源
├── docs/
│   ├── design.md             # 设计文档索引
│   └── api_protocol.md       # REST 与 WebSocket 协议草案
├── tests/
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   └── scenarios/            # 场景验收测试
├── CandleTRPG_LAN_System_Design.docx
├── main.py
└── README.md
```

## MVP 范围

- 单房主服务端
- 单跑团房间
- 2-6 名玩家加入
- 玩家行动提交与准备状态
- 房主触发 AI 回合结算
- AI 结算文本广播给所有客户端
- 每回合写入 `event_log.jsonl`
- 基础状态快照与上一轮回滚

## 非 MVP 范围

- 公网联机与账号系统
- 复杂地图、语音、剧本市场和云同步
- 完整规则书自动化
- 复杂权限系统
- 多房间并发运营

## 核心流程

1. 房主启动服务端，创建或加载战役。
2. 玩家通过局域网地址加入房间。
3. 服务端同步当前剧情、角色状态、玩家列表和回合阶段。
4. 玩家提交本轮行动并准备。
5. 全员准备或房主强制结算后，服务端锁定回合。
6. `GMAgent` 读取世界设定、场景、角色状态、历史摘要和玩家行动，调用 AI 生成结算结果。
7. 房主审核或修正 AI 输出。
8. 服务端保存事件日志和状态快照，并广播下一轮剧情。

## 设计文档

完整设计见根目录：

- `CandleTRPG_LAN_System_Design.docx`

已拆出的协议草案和结构说明见：

- `docs/design.md`
- `docs/api_protocol.md`

## 后续开发建议

1. 先实现后端 FastAPI 启动入口和静态页面托管。
2. 实现 WebSocket 连接、玩家加入和房间状态广播。
3. 实现 `TurnManager` 的行动提交、准备、锁定和阶段切换。
4. 接入可替换的 `AIClient`，先完成文本结算闭环。
5. 增加 JSONL 事件日志和状态快照。
6. 最后补房主审核、修正和回滚能力。
