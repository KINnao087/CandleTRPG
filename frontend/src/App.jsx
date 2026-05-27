import React, { useEffect, useMemo, useState } from "react";
import { roomApi } from "./api/client.js";
import { createRoomSocket } from "./websocket/roomSocket.js";

const demoState = {
  room_id: "room_001",
  turn_index: 1,
  phase: "planning",
  world: {
    title: "霓虹旧城",
    setting: "近未来都市旧城区被企业、帮派和地下情报贩子共同控制。",
  },
  scene: {
    time: "夜晚 21:30",
    location: "MIX 酒馆",
    description:
      "酒馆里很安静，窗外的霓虹招牌时明时暗。吧台后方有一扇狭窄的后门，门后通向一条没有监控的暗巷。",
  },
  players: [
    {
      id: "player_001",
      name: "林烛",
      character_name: "林烛",
      role: "player",
      ready: false,
      action_text: "",
    },
    {
      id: "host",
      name: "房主",
      character_name: "主持人",
      role: "host",
      ready: true,
      action_text: "",
    },
  ],
  characters: [
    {
      id: "char_001",
      player_id: "player_001",
      name: "林烛",
      status: { hp: 85, conditions: [] },
      inventory: ["终端", "短刀", "急救喷雾"],
    },
  ],
  timeline: [
    {
      id: "event_001",
      type: "scene",
      title: "当前场景",
      content: "线索集中在吧台后门与暗巷。玩家可以调查、交涉、潜行或准备战斗。",
      timestamp: "21:30",
    },
  ],
};

const phaseLabels = {
  lobby: "集结",
  planning: "行动填写",
  locked: "等待结算",
  resolving: "AI 结算中",
  review: "房主审核",
};

function generateRoomId() {
  return `room_${Math.random().toString(36).slice(2, 8)}`;
}

function getCurrentPlayer(players, playerId) {
  return players.find((player) => player.id === playerId) || players[0];
}

function mergeRoomState(current, next) {
  if (!next || typeof next !== "object") {
    return current;
  }

  return {
    ...current,
    ...next,
    world: { ...(current.world || {}), ...(next.world || {}) },
    scene: { ...current.scene, ...(next.scene || {}) },
    players: next.players || current.players,
    characters: next.characters || current.characters,
    timeline: next.timeline || current.timeline,
  };
}

function StatusPill({ tone = "neutral", children }) {
  return <span className={`status-pill ${tone}`}>{children}</span>;
}

function Field({ label, children }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children}
    </label>
  );
}

function MainMenu({
  roomId,
  setRoomId,
  playerName,
  setPlayerName,
  characterName,
  setCharacterName,
  role,
  setRole,
  notice,
  isBusy,
  onFindRoom,
  onOpenCreate,
}) {
  return (
    <main className="menu-shell">
      <section className="menu-hero">
        <span className="eyebrow">CandleTRPG LAN</span>
        <h1>烛火跑团</h1>
        <p>输入你的玩家信息，查找已有房间，或创建一个带世界设定的新局域网跑团房间。</p>
      </section>

      <form className="menu-form panel" onSubmit={onFindRoom}>
        <div className="panel-heading">
          <h2>主菜单</h2>
          <StatusPill>本地联机</StatusPill>
        </div>

        <Field label="用户名">
          <input
            value={playerName}
            onChange={(event) => setPlayerName(event.target.value)}
            placeholder="例如：张三"
          />
        </Field>

        <Field label="角色名">
          <input
            value={characterName}
            onChange={(event) => setCharacterName(event.target.value)}
            placeholder="例如：林烛"
          />
        </Field>

        <Field label="房间 ID">
          <input
            value={roomId}
            onChange={(event) => setRoomId(event.target.value)}
            placeholder="加入已有房间时必填"
          />
        </Field>

        <Field label="身份">
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="player">玩家</option>
            <option value="host">房主</option>
          </select>
        </Field>

        <div className="button-row menu-actions">
          <button type="submit" disabled={isBusy}>
            查找并加入
          </button>
          <button type="button" className="secondary" onClick={onOpenCreate} disabled={isBusy}>
            创建房间
          </button>
        </div>

        <p className="menu-notice">{notice}</p>
      </form>
    </main>
  );
}

function CreateRoomMenu({
  roomId,
  setRoomId,
  playerName,
  setPlayerName,
  characterName,
  setCharacterName,
  worldTitle,
  setWorldTitle,
  worldSetting,
  setWorldSetting,
  openingScene,
  setOpeningScene,
  notice,
  isBusy,
  onCreateRoom,
  onBack,
  onImportWorldFile,
}) {
  return (
    <main className="menu-shell create-shell">
      <section className="menu-hero">
        <span className="eyebrow">Room Setup</span>
        <h1>创建房间</h1>
        <p>创建者会自动成为房主。先导入或填写世界设定，再进入正式跑团页面。</p>
      </section>

      <form className="menu-form panel setup-form" onSubmit={onCreateRoom}>
        <div className="panel-heading">
          <h2>房间创建</h2>
          <StatusPill tone="good">房主模式</StatusPill>
        </div>

        <div className="setup-grid">
          <Field label="用户名">
            <input
              value={playerName}
              onChange={(event) => setPlayerName(event.target.value)}
              placeholder="例如：张三"
            />
          </Field>

          <Field label="角色名">
            <input
              value={characterName}
              onChange={(event) => setCharacterName(event.target.value)}
              placeholder="例如：林烛"
            />
          </Field>
        </div>

        <Field label="房间 ID">
          <div className="inline-control">
            <input
              value={roomId}
              onChange={(event) => setRoomId(event.target.value)}
              placeholder="留空会自动生成"
            />
            <button type="button" className="secondary" onClick={() => setRoomId(generateRoomId())}>
              生成
            </button>
          </div>
        </Field>

        <Field label="世界名称">
          <input
            value={worldTitle}
            onChange={(event) => setWorldTitle(event.target.value)}
            placeholder="例如：霓虹旧城"
          />
        </Field>

        <Field label="导入世界设定">
          <input type="file" accept=".txt,.md,.json" onChange={onImportWorldFile} />
        </Field>

        <Field label="世界设定">
          <textarea
            value={worldSetting}
            onChange={(event) => setWorldSetting(event.target.value)}
            placeholder="粘贴世界观、势力、规则基调、禁忌内容、AI 主持风格等。"
            rows={9}
          />
        </Field>

        <Field label="开场场景">
          <textarea
            value={openingScene}
            onChange={(event) => setOpeningScene(event.target.value)}
            placeholder="描述玩家进入游戏后看到的第一幕。"
            rows={4}
          />
        </Field>

        <div className="button-row menu-actions">
          <button type="submit" disabled={isBusy}>
            创建并进入游戏
          </button>
          <button type="button" className="secondary" onClick={onBack} disabled={isBusy}>
            返回主菜单
          </button>
        </div>

        <p className="menu-notice">{notice}</p>
      </form>
    </main>
  );
}

function PlayerList({ players }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>玩家</h2>
        <StatusPill tone={players.every((player) => player.ready) ? "good" : "warn"}>
          {players.filter((player) => player.ready).length}/{players.length} 已准备
        </StatusPill>
      </div>

      <div className="player-list">
        {players.map((player) => (
          <div className="player-row" key={player.id}>
            <div>
              <strong>{player.character_name || player.name}</strong>
              <span>{player.name}</span>
            </div>
            <StatusPill tone={player.ready ? "good" : "neutral"}>
              {player.ready ? "已准备" : "未准备"}
            </StatusPill>
          </div>
        ))}
      </div>
    </section>
  );
}

function CharacterPanel({ characters }) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>角色状态</h2>
      </div>

      <div className="character-grid">
        {characters.map((character) => (
          <article className="character-card" key={character.id}>
            <div className="character-card-header">
              <strong>{character.name}</strong>
              <StatusPill tone="good">HP {character.status?.hp ?? "-"}</StatusPill>
            </div>
            <p>
              {(character.status?.conditions || []).length
                ? character.status.conditions.join("、")
                : "无异常状态"}
            </p>
            <div className="tag-list">
              {(character.inventory || []).map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function Timeline({ events }) {
  return (
    <section className="panel timeline-panel">
      <div className="panel-heading">
        <h2>记录</h2>
      </div>

      <div className="timeline">
        {events.map((event) => (
          <article className="timeline-item" key={event.id || `${event.title}-${event.timestamp}`}>
            <time>{event.timestamp || "刚刚"}</time>
            <div>
              <strong>{event.title || event.type}</strong>
              <p>{event.content || event.narration || ""}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function RoomSummary({ roomId, playerName, characterName, role, worldTitle, turnIndex, onLeave }) {
  return (
    <section className="panel room-summary">
      <div className="panel-heading">
        <h2>房间</h2>
        <StatusPill>第 {turnIndex} 回合</StatusPill>
      </div>

      <dl>
        <div>
          <dt>房间 ID</dt>
          <dd>{roomId}</dd>
        </div>
        <div>
          <dt>世界</dt>
          <dd>{worldTitle || "未命名世界"}</dd>
        </div>
        <div>
          <dt>用户名</dt>
          <dd>{playerName}</dd>
        </div>
        <div>
          <dt>角色名</dt>
          <dd>{characterName}</dd>
        </div>
        <div>
          <dt>身份</dt>
          <dd>{role === "host" ? "房主" : "玩家"}</dd>
        </div>
      </dl>

      <button type="button" className="secondary full-width" onClick={onLeave}>
        返回主菜单
      </button>
    </section>
  );
}

function App() {
  const [screen, setScreen] = useState("main");
  const [roomId, setRoomId] = useState("");
  const [playerName, setPlayerName] = useState("");
  const [characterName, setCharacterName] = useState("");
  const [worldTitle, setWorldTitle] = useState("霓虹旧城");
  const [worldSetting, setWorldSetting] = useState("");
  const [openingScene, setOpeningScene] = useState("");
  const [playerId, setPlayerId] = useState("player_001");
  const [role, setRole] = useState("player");
  const [roomState, setRoomState] = useState(demoState);
  const [actionText, setActionText] = useState("");
  const [hostNote, setHostNote] = useState("");
  const [socketStatus, setSocketStatus] = useState("closed");
  const [notice, setNotice] = useState("请输入用户名、角色名和房间信息。");
  const [isBusy, setIsBusy] = useState(false);

  const currentPlayer = useMemo(
    () => getCurrentPlayer(roomState.players, playerId),
    [roomState.players, playerId],
  );

  const readyCount = roomState.players.filter((player) => player.ready).length;
  const canResolve = role === "host" && roomState.phase !== "resolving";

  useEffect(() => {
    if (screen !== "room" || !roomId) {
      return undefined;
    }

    let isMounted = true;

    roomApi
      .getState(roomId)
      .then((state) => {
        if (!isMounted) return;
        setRoomState((current) => mergeRoomState(current, state));
        setNotice("已读取后端房间状态。");
      })
      .catch(() => {
        if (!isMounted) return;
        setRoomState((current) => ({ ...current, room_id: roomId }));
      });

    return () => {
      isMounted = false;
    };
  }, [screen, roomId]);

  useEffect(() => {
    if (screen !== "room" || !roomId) {
      setSocketStatus("closed");
      return undefined;
    }

    const socket = createRoomSocket({
      roomId,
      playerId,
      onStatus: setSocketStatus,
      onMessage: (message) => {
        if (message.type === "room_state" || message.type === "turn_resolved") {
          setRoomState((current) => mergeRoomState(current, message.payload));
          setNotice("已通过 WebSocket 同步最新房间状态。");
          return;
        }

        if (message.type === "error") {
          setNotice(message.payload?.message || "服务器返回了错误消息。");
        }
      },
    });

    return () => socket?.close();
  }, [screen, roomId, playerId]);

  function validateIdentity() {
    if (!playerName.trim()) {
      setNotice("请先输入用户名。");
      return false;
    }

    if (!characterName.trim()) {
      setNotice("请先输入角色名。");
      return false;
    }

    return true;
  }

  async function findRoom(event) {
    event.preventDefault();

    if (!validateIdentity()) {
      return;
    }

    const effectiveRoomId = roomId.trim();
    if (!effectiveRoomId) {
      setNotice("查找房间需要输入房间 ID。");
      return;
    }

    setIsBusy(true);

    try {
      const state = await roomApi.getState(effectiveRoomId);
      setRoomState((current) => mergeRoomState(current, state));

      const joined = await roomApi.joinRoom(effectiveRoomId, {
        player_name: playerName.trim(),
        character_name: characterName.trim(),
        role,
      });

      setRoomId(effectiveRoomId);
      setPlayerId(joined.player_id || joined.id || playerId);
      setRoomState((current) => mergeRoomState(current, joined.room_state));
      setScreen("room");
      setNotice("已加入房间。");
    } catch {
      setNotice("没有找到可加入的后端房间，或后端暂不可用。");
    } finally {
      setIsBusy(false);
    }
  }

  function openCreateRoom(event) {
    event.preventDefault();
    if (!roomId.trim()) {
      setRoomId(generateRoomId());
    }
    setRole("host");
    setNotice("创建房间前，请先导入或填写世界设定。");
    setScreen("create");
  }

  async function importWorldFile(event) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }

    const text = await file.text();
    setWorldSetting(text);
    if (!worldTitle.trim()) {
      setWorldTitle(file.name.replace(/\.[^.]+$/, ""));
    }
    setNotice(`已导入世界设定：${file.name}`);
  }

  async function createRoom(event) {
    event.preventDefault();

    if (!validateIdentity()) {
      return;
    }

    const effectiveRoomId = roomId.trim() || generateRoomId();
    const trimmedWorldTitle = worldTitle.trim() || "未命名世界";
    const trimmedWorldSetting = worldSetting.trim();
    const trimmedOpeningScene = openingScene.trim();

    if (!trimmedWorldSetting) {
      setNotice("创建房间前需要填写或导入世界设定。");
      return;
    }

    setIsBusy(true);
    setRole("host");
    setRoomId(effectiveRoomId);

    let nextRoomState = null;

    try {
      const created = await roomApi.createRoom(effectiveRoomId, {
        host_name: playerName.trim(),
        character_name: characterName.trim(),
        world: {
          title: trimmedWorldTitle,
          setting: trimmedWorldSetting,
          opening_scene: trimmedOpeningScene,
        },
      });
      nextRoomState = created.room_state || created;
    } catch {
      nextRoomState = null;
    }

    try {
      const imported = await roomApi.importWorld(effectiveRoomId, {
        title: trimmedWorldTitle,
        setting: trimmedWorldSetting,
        opening_scene: trimmedOpeningScene,
      });
      nextRoomState = imported.room_state || imported || nextRoomState;
    } catch {
      nextRoomState = nextRoomState || null;
    }

    try {
      const joined = await roomApi.joinRoom(effectiveRoomId, {
        player_name: playerName.trim(),
        character_name: characterName.trim(),
        role: "host",
      });

      setPlayerId(joined.player_id || joined.id || "player_001");
      setRoomState((current) =>
        mergeRoomState(
          mergeRoomState(current, nextRoomState),
          joined.room_state || {
            room_id: effectiveRoomId,
            world: {
              title: trimmedWorldTitle,
              setting: trimmedWorldSetting,
            },
          },
        ),
      );
      setScreen("room");
      setNotice("房间已创建，世界设定已导入。");
    } catch {
      setPlayerId("host");
      setRoomState({
        ...demoState,
        room_id: effectiveRoomId,
        world: {
          title: trimmedWorldTitle,
          setting: trimmedWorldSetting,
        },
        scene: {
          ...demoState.scene,
          description: trimmedOpeningScene || demoState.scene.description,
        },
        players: demoState.players.map((player) =>
          player.id === "host"
            ? {
                ...player,
                name: playerName.trim(),
                character_name: characterName.trim(),
                role: "host",
              }
            : player,
        ),
      });
      setScreen("room");
      setNotice("后端暂不可用，已进入本地演示房间。");
    } finally {
      setIsBusy(false);
    }
  }

  function leaveRoom() {
    setScreen("main");
    setSocketStatus("closed");
    setActionText("");
    setHostNote("");
    setNotice("已返回主菜单。");
  }

  async function submitAction() {
    if (!actionText.trim()) {
      setNotice("行动内容不能为空。");
      return;
    }

    setIsBusy(true);
    const payload = {
      player_id: playerId,
      character_name: currentPlayer?.character_name || characterName,
      action_text: actionText.trim(),
      turn_index: roomState.turn_index,
    };

    try {
      const state = await roomApi.submitAction(roomId, payload);
      setRoomState((current) => mergeRoomState(current, state));
      setNotice("行动已提交。");
    } catch {
      setRoomState((current) => ({
        ...current,
        players: current.players.map((player) =>
          player.id === playerId ? { ...player, action_text: payload.action_text } : player,
        ),
      }));
      setNotice("后端暂不可用，行动已暂存在本地界面。");
    } finally {
      setIsBusy(false);
    }
  }

  async function toggleReady() {
    const ready = !currentPlayer?.ready;
    setIsBusy(true);

    try {
      const state = await roomApi.updateReady(roomId, { player_id: playerId, ready });
      setRoomState((current) => mergeRoomState(current, state));
      setNotice(ready ? "已标记准备。" : "已取消准备。");
    } catch {
      setRoomState((current) => ({
        ...current,
        players: current.players.map((player) =>
          player.id === playerId ? { ...player, ready } : player,
        ),
      }));
      setNotice(ready ? "已在本地标记准备。" : "已在本地取消准备。");
    } finally {
      setIsBusy(false);
    }
  }

  async function resolveTurn() {
    setIsBusy(true);
    setRoomState((current) => ({ ...current, phase: "resolving" }));

    try {
      const state = await roomApi.resolveTurn({
        room_id: roomId,
        host_note: hostNote,
        force: readyCount < roomState.players.length,
      });

      setRoomState((current) => mergeRoomState(current, state));
      setNotice("本回合已结算。");
    } catch {
      setRoomState((current) => ({
        ...current,
        phase: "review",
        turn_index: current.turn_index + 1,
        timeline: [
          {
            id: `local_${Date.now()}`,
            type: "turn_resolved",
            title: `第 ${current.turn_index} 回合结算`,
            content: "本地演示：后端接入后这里会显示 AI 主持人的结算文本和状态变更。",
            timestamp: new Date().toLocaleTimeString("zh-CN", {
              hour: "2-digit",
              minute: "2-digit",
            }),
          },
          ...current.timeline,
        ],
      }));
      setNotice("后端暂不可用，已生成本地演示结算。");
    } finally {
      setIsBusy(false);
    }
  }

  async function rollbackTurn() {
    setIsBusy(true);

    try {
      const state = await roomApi.rollback({
        room_id: roomId,
        turn_index: Math.max(1, roomState.turn_index - 1),
      });

      setRoomState((current) => mergeRoomState(current, state));
      setNotice("已回滚到上一回合。");
    } catch {
      setRoomState((current) => ({
        ...current,
        turn_index: Math.max(1, current.turn_index - 1),
        phase: "planning",
      }));
      setNotice("后端暂不可用，已在本地回滚显示。");
    } finally {
      setIsBusy(false);
    }
  }

  if (screen === "main") {
    return (
      <MainMenu
        roomId={roomId}
        setRoomId={setRoomId}
        playerName={playerName}
        setPlayerName={setPlayerName}
        characterName={characterName}
        setCharacterName={setCharacterName}
        role={role}
        setRole={setRole}
        notice={notice}
        isBusy={isBusy}
        onFindRoom={findRoom}
        onOpenCreate={openCreateRoom}
      />
    );
  }

  if (screen === "create") {
    return (
      <CreateRoomMenu
        roomId={roomId}
        setRoomId={setRoomId}
        playerName={playerName}
        setPlayerName={setPlayerName}
        characterName={characterName}
        setCharacterName={setCharacterName}
        worldTitle={worldTitle}
        setWorldTitle={setWorldTitle}
        worldSetting={worldSetting}
        setWorldSetting={setWorldSetting}
        openingScene={openingScene}
        setOpeningScene={setOpeningScene}
        notice={notice}
        isBusy={isBusy}
        onCreateRoom={createRoom}
        onBack={() => {
          setScreen("main");
          setNotice("已返回主菜单。");
        }}
        onImportWorldFile={importWorldFile}
      />
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">CandleTRPG LAN</span>
          <h1>跑团控制台</h1>
        </div>
        <div className="topbar-status">
          <StatusPill tone={socketStatus === "connected" ? "good" : "warn"}>
            WS {socketStatus}
          </StatusPill>
          <StatusPill>{phaseLabels[roomState.phase] || roomState.phase}</StatusPill>
        </div>
      </header>

      <section className="notice-bar">
        <span>{notice}</span>
      </section>

      <div className="layout">
        <aside className="sidebar">
          <RoomSummary
            roomId={roomId}
            playerName={playerName}
            characterName={characterName}
            role={role}
            worldTitle={roomState.world?.title || worldTitle}
            turnIndex={roomState.turn_index}
            onLeave={leaveRoom}
          />

          <PlayerList players={roomState.players} />
          <CharacterPanel characters={roomState.characters} />
        </aside>

        <section className="main-stage">
          <section className="scene-panel">
            <div className="scene-meta">
              <StatusPill>{roomState.scene.time}</StatusPill>
              <StatusPill>{roomState.scene.location}</StatusPill>
            </div>
            <h2>{roomState.scene.location}</h2>
            <p>{roomState.scene.description}</p>
          </section>

          <div className="workspace-grid">
            <section className="panel action-panel">
              <div className="panel-heading">
                <h2>本轮行动</h2>
                <StatusPill tone={currentPlayer?.ready ? "good" : "neutral"}>
                  {currentPlayer?.ready ? "已锁定" : "可编辑"}
                </StatusPill>
              </div>

              <textarea
                value={actionText}
                onChange={(event) => setActionText(event.target.value)}
                placeholder="输入本回合行动，例如：检查后门是否有脚印，并让队友留意吧台。"
                rows={8}
              />

              <div className="button-row">
                <button type="button" onClick={submitAction} disabled={isBusy || currentPlayer?.ready}>
                  提交行动
                </button>
                <button type="button" className="secondary" onClick={toggleReady} disabled={isBusy}>
                  {currentPlayer?.ready ? "取消准备" : "准备"}
                </button>
              </div>
            </section>

            <section className="panel host-panel">
              <div className="panel-heading">
                <h2>房主</h2>
                <StatusPill tone={role === "host" ? "good" : "neutral"}>
                  {role === "host" ? "可操作" : "只读"}
                </StatusPill>
              </div>

              <textarea
                value={hostNote}
                onChange={(event) => setHostNote(event.target.value)}
                placeholder="房主补充，例如：优先处理潜行失败的风险，保留暗巷中的伏笔。"
                rows={5}
                disabled={role !== "host"}
              />

              <div className="button-row">
                <button type="button" onClick={resolveTurn} disabled={isBusy || !canResolve}>
                  结算回合
                </button>
                <button type="button" className="secondary" onClick={rollbackTurn} disabled={isBusy || role !== "host"}>
                  回滚
                </button>
              </div>
            </section>
          </div>

          <Timeline events={roomState.timeline} />
        </section>
      </div>
    </main>
  );
}

export default App;
