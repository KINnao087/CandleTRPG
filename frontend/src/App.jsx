import React, { useEffect, useMemo, useState } from "react";
import { roomApi } from "./api/client.js";
import { createRoomSocket } from "./websocket/roomSocket.js";

const demoState = {
  room_id: "room_001",
  turn_index: 1,
  phase: "planning",
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

function App() {
  const [roomId, setRoomId] = useState("room_001");
  const [playerName, setPlayerName] = useState("林烛");
  const [characterName, setCharacterName] = useState("林烛");
  const [playerId, setPlayerId] = useState("player_001");
  const [role, setRole] = useState("player");
  const [roomState, setRoomState] = useState(demoState);
  const [actionText, setActionText] = useState("");
  const [hostNote, setHostNote] = useState("");
  const [socketStatus, setSocketStatus] = useState("closed");
  const [notice, setNotice] = useState("当前展示演示数据，连接后端后会自动同步真实房间状态。");
  const [isBusy, setIsBusy] = useState(false);

  const currentPlayer = useMemo(
    () => getCurrentPlayer(roomState.players, playerId),
    [roomState.players, playerId],
  );

  const readyCount = roomState.players.filter((player) => player.ready).length;
  const canResolve = role === "host" && roomState.phase !== "resolving";

  useEffect(() => {
    let isMounted = true;

    roomApi.getState(roomId)
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
  }, [roomId]);

  useEffect(() => {
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
  }, [roomId, playerId]);

  async function joinRoom(event) {
    event.preventDefault();
    setIsBusy(true);

    try {
      const joined = await roomApi.joinRoom(roomId, {
        player_name: playerName,
        character_name: characterName,
        role,
      });

      setPlayerId(joined.player_id || joined.id || playerId);
      setRoomState((current) => mergeRoomState(current, joined.room_state));
      setNotice("已加入房间。");
    } catch {
      const localPlayerId = role === "host" ? "host" : "player_001";
      setPlayerId(localPlayerId);
      setRoomState((current) => ({
        ...current,
        room_id: roomId,
        players: current.players.map((player) =>
          player.id === localPlayerId
            ? { ...player, name: playerName, character_name: characterName, role }
            : player,
        ),
      }));
      setNotice("后端暂不可用，已在本地演示模式中加入房间。");
    } finally {
      setIsBusy(false);
    }
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
          <form className="panel join-panel" onSubmit={joinRoom}>
            <div className="panel-heading">
              <h2>房间</h2>
              <StatusPill>第 {roomState.turn_index} 回合</StatusPill>
            </div>

            <Field label="房间 ID">
              <input value={roomId} onChange={(event) => setRoomId(event.target.value)} />
            </Field>
            <Field label="玩家名">
              <input value={playerName} onChange={(event) => setPlayerName(event.target.value)} />
            </Field>
            <Field label="角色名">
              <input value={characterName} onChange={(event) => setCharacterName(event.target.value)} />
            </Field>
            <Field label="身份">
              <select value={role} onChange={(event) => setRole(event.target.value)}>
                <option value="player">玩家</option>
                <option value="host">房主</option>
              </select>
            </Field>

            <button type="submit" disabled={isBusy}>加入/刷新</button>
          </form>

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
