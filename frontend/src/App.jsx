import React, { useEffect, useMemo, useState } from "react";
import { DEFAULT_API_BASE_URL, roomApi } from "./api/client.js";
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
      abilities: [
        {
          name: "飞行",
          description: "可以进行不超过音速的低空飞行。",
        },
      ],
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

const themeOptions = [
  { id: "apple", label: "🍎 苹果" },
  { id: "cyberBlue", label: "💜 蓝紫赛博朋克" },
  { id: "cyberRed", label: "❤️ 红黑赛博朋克" },
  { id: "customWhite", label: "🤍 白底自定义" },
  { id: "customGray", label: "🩶 灰底自定义" },
  { id: "emeraldForest", label: "🌿 翡翠森林" },
  { id: "royalAmethyst", label: "👑 皇家紫金" },
  { id: "neonSynthwave", label: "💖 霓虹合成波" },
  { id: "frostAurora", label: "❄️ 冰霜极光" },
  { id: "sunsetEmber", label: "🔥 落日余晖" },
  { id: "midnightVoid", label: "🌑 午夜虚空" },
];

function generateRoomId() {
  return `room_${Math.random().toString(36).slice(2, 8)}`;
}

function getCurrentPlayer(players, playerId) {
  return players.find((player) => player.id === playerId) || players[0];
}

function getRoomStatePayload(response) {
  if (!response || typeof response !== "object") {
    return null;
  }

  return response.room_state && typeof response.room_state === "object"
    ? response.room_state
    : response;
}

function mergeRoomState(current, response) {
  const next = getRoomStatePayload(response);

  if (!next) {
    return current;
  }

  return {
    ...current,
    ...next,
    world: { ...(current.world || {}), ...(next.world || {}) },
    scene: { ...current.scene, ...(next.scene || {}) },
    players: next.players || current.players,
    characters: next.characters || current.characters,
    timeline: Array.isArray(next.timeline) ? next.timeline : current.timeline,
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

function normalizeSubAbilities(ability) {
  const rawSubAbilities = ability?.sub_ability ?? ability?.sub_abilities ?? [];

  if (Array.isArray(rawSubAbilities)) {
    return rawSubAbilities;
  }

  if (typeof rawSubAbilities === "string" && rawSubAbilities.trim()) {
    return [{ name: rawSubAbilities.trim() }];
  }

  if (rawSubAbilities && typeof rawSubAbilities === "object") {
    return Object.entries(rawSubAbilities).map(([name, value]) =>
      value && typeof value === "object"
        ? { name, ...value }
        : { name, description: String(value ?? "") },
    );
  }

  return [];
}

function isMarkdownBlockStart(line) {
  return (
    /^```/.test(line) ||
    /^#{1,4}\s+/.test(line) ||
    /^>\s?/.test(line) ||
    /^\s*[-*+]\s+/.test(line) ||
    /^\s*\d+[.)]\s+/.test(line)
  );
}

function isSafeMarkdownUrl(url) {
  return /^(https?:|mailto:|tel:|\/|#)/i.test(url.trim());
}

function renderInlineMarkdown(text, keyPrefix = "inline") {
  const value = String(text ?? "");
  const nodes = [];
  let index = 0;

  function pushText(end) {
    if (end > index) {
      nodes.push(value.slice(index, end));
      index = end;
    }
  }

  while (index < value.length) {
    if (value.startsWith("`", index)) {
      const end = value.indexOf("`", index + 1);
      if (end > index) {
        nodes.push(<code key={`${keyPrefix}-code-${index}`}>{value.slice(index + 1, end)}</code>);
        index = end + 1;
        continue;
      }
    }

    if (value.startsWith("**", index)) {
      const end = value.indexOf("**", index + 2);
      if (end > index) {
        nodes.push(
          <strong key={`${keyPrefix}-strong-${index}`}>
            {renderInlineMarkdown(value.slice(index + 2, end), `${keyPrefix}-strong-${index}`)}
          </strong>,
        );
        index = end + 2;
        continue;
      }
    }

    if (value.startsWith("*", index)) {
      const end = value.indexOf("*", index + 1);
      if (end > index) {
        nodes.push(
          <em key={`${keyPrefix}-em-${index}`}>
            {renderInlineMarkdown(value.slice(index + 1, end), `${keyPrefix}-em-${index}`)}
          </em>,
        );
        index = end + 1;
        continue;
      }
    }

    if (value.startsWith("[", index)) {
      const textEnd = value.indexOf("]", index + 1);
      const urlStart = textEnd >= 0 ? value.indexOf("(", textEnd) : -1;
      const urlEnd = urlStart >= 0 ? value.indexOf(")", urlStart) : -1;
      if (textEnd > index && urlStart === textEnd + 1 && urlEnd > urlStart) {
        const label = value.slice(index + 1, textEnd);
        const url = value.slice(urlStart + 1, urlEnd);
        nodes.push(
          isSafeMarkdownUrl(url) ? (
            <a key={`${keyPrefix}-link-${index}`} href={url} target="_blank" rel="noreferrer">
              {renderInlineMarkdown(label, `${keyPrefix}-link-${index}`)}
            </a>
          ) : (
            label
          ),
        );
        index = urlEnd + 1;
        continue;
      }
    }

    const nextMarkers = ["`", "**", "*", "["]
      .map((marker) => value.indexOf(marker, index + 1))
      .filter((position) => position > -1);
    pushText(nextMarkers.length ? Math.min(...nextMarkers) : value.length);
  }

  return nodes;
}

function MarkdownText({ text, fallback = "暂无内容。", className = "" }) {
  const content = String(text || fallback).trim();

  if (!content) {
    return <div className={`markdown-text ${className}`.trim()}>{fallback}</div>;
  }

  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fenceMatch = line.match(/^```(.*)$/);
    if (fenceMatch) {
      const codeLines = [];
      index += 1;
      while (index < lines.length && !/^```/.test(lines[index])) {
        codeLines.push(lines[index]);
        index += 1;
      }
      index += 1;
      blocks.push(
        <pre key={`code-${blocks.length}`}>
          <code>{codeLines.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    const headingMatch = line.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const HeadingTag = `h${headingMatch[1].length + 2}`;
      blocks.push(
        <HeadingTag key={`heading-${blocks.length}`}>
          {renderInlineMarkdown(headingMatch[2], `heading-${blocks.length}`)}
        </HeadingTag>,
      );
      index += 1;
      continue;
    }

    if (/^>\s?/.test(line)) {
      const quoteLines = [];
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quoteLines.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push(
        <blockquote key={`quote-${blocks.length}`}>
          <MarkdownText text={quoteLines.join("\n")} />
        </blockquote>,
      );
      continue;
    }

    const unorderedMatch = line.match(/^\s*[-*+]\s+(.+)$/);
    const orderedMatch = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unorderedMatch || orderedMatch) {
      const ordered = Boolean(orderedMatch);
      const items = [];
      while (index < lines.length) {
        const itemMatch = ordered
          ? lines[index].match(/^\s*\d+[.)]\s+(.+)$/)
          : lines[index].match(/^\s*[-*+]\s+(.+)$/);
        if (!itemMatch) break;
        items.push(itemMatch[1]);
        index += 1;
      }
      const ListTag = ordered ? "ol" : "ul";
      blocks.push(
        <ListTag key={`list-${blocks.length}`}>
          {items.map((item, itemIndex) => (
            <li key={`${blocks.length}-${itemIndex}`}>
              {renderInlineMarkdown(item, `list-${blocks.length}-${itemIndex}`)}
            </li>
          ))}
        </ListTag>,
      );
      continue;
    }

    const paragraphLines = [];
    while (index < lines.length && lines[index].trim() && !isMarkdownBlockStart(lines[index])) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    blocks.push(
      <p key={`paragraph-${blocks.length}`}>
        {renderInlineMarkdown(paragraphLines.join(" "), `paragraph-${blocks.length}`)}
      </p>,
    );
  }

  return <div className={`markdown-text ${className}`.trim()}>{blocks}</div>;
}

function ThemeSwitcher({ theme, setTheme, customColor, setCustomColor }) {
  const [isOpen, setIsOpen] = useState(false);
  const usesCustomColor = theme === "customWhite" || theme === "customGray";

  return (
    <div className="theme-switcher">
      <button
        type="button"
        className={isOpen ? "theme-toggle open" : "theme-toggle"}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((value) => !value)}
      >
        主题
      </button>
      <div className={isOpen ? "theme-menu open" : "theme-menu"} aria-hidden={!isOpen}>
        <strong>界面主题</strong>
        <div className="theme-options">
          {themeOptions.map((option) => (
            <button
              type="button"
              className={theme === option.id ? "theme-option active" : "theme-option"}
              key={option.id}
              onClick={() => setTheme(option.id)}
              tabIndex={isOpen ? 0 : -1}
            >
              {option.label}
            </button>
          ))}
        </div>
        {usesCustomColor && (
          <label className="theme-color">
            <span>自定义颜色</span>
            <input
              type="color"
              value={customColor}
              onChange={(event) => setCustomColor(event.target.value)}
              tabIndex={isOpen ? 0 : -1}
            />
          </label>
        )}
      </div>
    </div>
  );
}

function formatRoomUpdatedAt(value) {
  if (!value) {
    return "未知时间";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SavedRoomsPanel({ rooms, status, selectedRoomId, onSelectRoom, onRefresh, isBusy, isLoading }) {
  return (
    <section className="panel saved-rooms-panel">
      <div className="panel-heading">
        <h2>已保存房间</h2>
        <button
          type="button"
          className={isLoading ? "secondary compact-button loading" : "secondary compact-button"}
          onClick={onRefresh}
          disabled={isBusy || isLoading}
        >
          {isLoading && <span className="button-spinner" aria-hidden="true" />}
          <span>{isLoading ? "读取中" : "刷新"}</span>
        </button>
      </div>

      {status && <p className="saved-rooms-status">{status}</p>}

      <div className={isLoading ? "saved-room-list-shell loading" : "saved-room-list-shell"}>
        <div className="saved-room-list">
          {rooms.length > 0 ? (
            rooms.map((room) => {
              const roomKey = room.room_hash || room.room_id;
              return (
              <button
                type="button"
                className={roomKey === selectedRoomId ? "saved-room-card selected" : "saved-room-card"}
                key={roomKey}
                onClick={() => onSelectRoom(roomKey)}
                disabled={isBusy || isLoading}
              >
                <span className="saved-room-title">{room.title || room.room_id}</span>
                <span className="saved-room-id">{room.room_id}</span>
                <span className="saved-room-meta">
                  第 {room.turn_index ?? "-"} 回合 · {phaseLabels[room.phase] || room.phase || "未知阶段"}
                </span>
                <span className="saved-room-meta">
                  玩家 {room.player_count ?? 0} 人 · 在线 {room.online_player_count ?? 0} 人
                </span>
                <span className="saved-room-time">{formatRoomUpdatedAt(room.updated_at)}</span>
              </button>
              );
            })
          ) : (
            <p className="saved-rooms-empty">当前服务器还没有可显示的已保存房间。</p>
          )}
        </div>

        <div className="saved-room-loading" aria-live="polite" aria-hidden={!isLoading}>
          <span className="saved-room-loading-ring" aria-hidden="true" />
          <strong>正在同步房间列表</strong>
          <span>等待后端返回最新摘要</span>
        </div>
      </div>
    </section>
  );
}

function MainMenu({
  serverUrl,
  setServerUrl,
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
  savedRooms,
  savedRoomsStatus,
  selectedSavedRoomId,
  isLoadingSavedRooms,
  onSelectSavedRoom,
  onRefreshSavedRooms,
  themeClass,
  themeStyle,
  themeSwitcher,
}) {
  return (
    <main className={`menu-shell ${themeClass}`} style={themeStyle}>
      {themeSwitcher}
      <div className="menu-left">
        <section className="menu-hero">
          <span className="eyebrow">CandleTRPG LAN</span>
          <h1>烛火跑团</h1>
          <p>输入你的玩家信息，查找已有房间，或创建一个带世界设定的新局域网跑团房间。</p>
        </section>

        <SavedRoomsPanel
          rooms={savedRooms}
          status={savedRoomsStatus}
          selectedRoomId={selectedSavedRoomId}
          onSelectRoom={onSelectSavedRoom}
          onRefresh={onRefreshSavedRooms}
          isBusy={isBusy}
          isLoading={isLoadingSavedRooms}
        />
      </div>

      <form className="menu-form panel" onSubmit={onFindRoom}>
        <div className="panel-heading">
          <h2>主菜单</h2>
          <StatusPill>本地联机</StatusPill>
        </div>

        <Field label="服务器地址">
          <input
            value={serverUrl}
            onChange={(event) => setServerUrl(event.target.value)}
            placeholder="例如：http://192.168.1.23:8001"
          />
        </Field>

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

        <Field label="房间 Hash">
          <input
            value={roomId}
            onChange={(event) => {
              setRoomId(event.target.value);
              setSelectedSavedRoomId("");
            }}
            placeholder="加入已有房间时必填"
            className={selectedSavedRoomId ? "room-id-input selected" : "room-id-input"}
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
  serverUrl,
  setServerUrl,
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
  themeClass,
  themeStyle,
  themeSwitcher,
}) {
  return (
    <main className={`menu-shell create-shell ${themeClass}`} style={themeStyle}>
      {themeSwitcher}
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
          <Field label="服务器地址">
            <input
              value={serverUrl}
              onChange={(event) => setServerUrl(event.target.value)}
              placeholder="例如：http://192.168.1.23:8001"
            />
          </Field>

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
              {(character.abilities || []).length > 0 && (
                <div className="ability-list">
                  <h3>能力</h3>
                  {character.abilities.map((ability) => (
                    <div className="ability-item" key={`${character.id}-${ability.name}`}>
                      <strong>{ability.name}</strong>
                      {ability.description && <MarkdownText text={ability.description} />}
                      {normalizeSubAbilities(ability).length > 0 && (
                        <div className="sub-ability-list">
                          {normalizeSubAbilities(ability).map((subAbility, index) => (
                            <div
                              className="sub-ability-item"
                              key={`${character.id}-${ability.name}-sub-${subAbility.name || index}`}
                            >
                              <strong>{subAbility.name || `子能力 ${index + 1}`}</strong>
                              {subAbility.description && <MarkdownText text={subAbility.description} />}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
    );
  }

function WorldPanel({ world }) {
  return (
    <section className="panel world-panel">
      <div className="panel-heading">
        <h2>世界设定</h2>
      </div>
      <strong>{world?.title || "未命名世界"}</strong>
      <MarkdownText text={world?.setting} fallback="暂无世界设定。" />
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
        {events.map((event, index) => (
          <article
            className="timeline-item"
            key={`${event.id || "timeline"}-${event.title || event.type || "event"}-${event.timestamp || index}-${index}`}
          >
            <time>{event.timestamp || "刚刚"}</time>
            <div>
              <strong>{event.title || event.type}</strong>
              <MarkdownText text={event.content || event.narration} fallback="" />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function RoomSummary({
  serverUrl,
  roomId,
  playerName,
  characterName,
  role,
  worldTitle,
  turnIndex,
  onLeave,
  isBusy,
}) {
  return (
    <section className="panel room-summary">
      <div className="panel-heading">
        <h2>房间</h2>
        <StatusPill>第 {turnIndex} 回合</StatusPill>
      </div>

      <dl>
        <div>
          <dt>服务器</dt>
          <dd>{serverUrl || "同源后端"}</dd>
        </div>
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

      <button type="button" className="secondary full-width" onClick={onLeave} disabled={isBusy}>
        返回主菜单
      </button>
    </section>
  );
}

function App() {
  const [screen, setScreen] = useState("main");
  const [serverUrl, setServerUrl] = useState(DEFAULT_API_BASE_URL || "http://127.0.0.1:8001");
  const [roomId, setRoomId] = useState("");
  const [roomHash, setRoomHash] = useState("");
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
  const [savedRooms, setSavedRooms] = useState([]);
  const [savedRoomsStatus, setSavedRoomsStatus] = useState("");
  const [isLoadingSavedRooms, setIsLoadingSavedRooms] = useState(false);
  const [selectedSavedRoomId, setSelectedSavedRoomId] = useState("");
  const [theme, setTheme] = useState("cyberBlue");
  const [customColor, setCustomColor] = useState("#2563eb");

  const currentPlayer = useMemo(
    () => getCurrentPlayer(roomState.players, playerId),
    [roomState.players, playerId],
  );

  const themeClass = `theme-${theme}`;
  const themeStyle = { "--custom-color": customColor };
  const themeSwitcher = (
    <ThemeSwitcher
      theme={theme}
      setTheme={setTheme}
      customColor={customColor}
      setCustomColor={setCustomColor}
    />
  );

  const readyCount = roomState.players.filter((player) => player.ready).length;
  const canResolve = role === "host" && roomState.phase !== "resolving";
  const latestTimelineEvent = Array.isArray(roomState.timeline) ? roomState.timeline[0] : null;
  const latestTimelineText =
    latestTimelineEvent?.content ||
    latestTimelineEvent?.narration ||
    "";

  async function loadSavedRooms() {
    setIsLoadingSavedRooms(true);
    setSavedRoomsStatus("正在读取已保存房间...");

    try {
      const result = await roomApi.getSavedRooms(serverUrl);
      const rooms = Array.isArray(result?.rooms) ? result.rooms : [];
      setSavedRooms(rooms);
      setSavedRoomsStatus(rooms.length ? "" : "当前服务器没有已保存房间。");
    } catch {
      setSavedRooms([]);
      setSavedRoomsStatus("读取已保存房间失败，请确认服务器地址和后端状态。");
    } finally {
      setIsLoadingSavedRooms(false);
    }
  }

  useEffect(() => {
    if (screen !== "main") {
      return undefined;
    }

    let isMounted = true;
    setIsLoadingSavedRooms(true);
    setSavedRoomsStatus("正在读取已保存房间...");

    roomApi
      .getSavedRooms(serverUrl)
      .then((result) => {
        if (!isMounted) return;
        const rooms = Array.isArray(result?.rooms) ? result.rooms : [];
        setSavedRooms(rooms);
        setSavedRoomsStatus(rooms.length ? "" : "当前服务器没有已保存房间。");
        setIsLoadingSavedRooms(false);
      })
      .catch(() => {
        if (!isMounted) return;
        setSavedRooms([]);
        setSavedRoomsStatus("读取已保存房间失败，请确认服务器地址和后端状态。");
        setIsLoadingSavedRooms(false);
      });

    return () => {
      isMounted = false;
    };
  }, [screen, serverUrl]);

  useEffect(() => {
    if (screen !== "room" || !roomHash) {
      return undefined;
    }

    let isMounted = true;

    roomApi
      .getState(roomHash, serverUrl)
      .then((state) => {
        if (!isMounted) return;
        setRoomState((current) => mergeRoomState(current, state));
        setRoomId((current) => state?.room_id || current);
        setRoomHash((current) => state?.room_hash || current);
        setNotice("已读取后端房间状态。");
      })
      .catch(() => {
        if (!isMounted) return;
        setNotice("读取后端房间状态失败，未修改本地房间状态。");
      });

    return () => {
      isMounted = false;
    };
  }, [screen, roomHash, serverUrl]);

  useEffect(() => {
    if (screen !== "room" || !roomHash) {
      setSocketStatus("closed");
      return undefined;
    }

    const socket = createRoomSocket({
      roomId: roomHash,
      playerId,
      serverUrl,
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
  }, [screen, roomHash, playerId, serverUrl]);

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

    const effectiveRoomHash = roomHash.trim();
    if (!effectiveRoomHash) {
      setNotice("查找房间需要输入房间 Hash。");
      return;
    }

    setIsBusy(true);

    try {
      const state = await roomApi.getState(effectiveRoomHash, serverUrl);
      const resolvedRoomHash = state?.room_hash || effectiveRoomHash;
      setRoomState((current) => mergeRoomState(current, state));
      setRoomId(state?.room_id || "");

      const joined = await roomApi.joinRoom(resolvedRoomHash, {
        player_name: playerName.trim(),
        character_name: characterName.trim(),
        role,
      }, serverUrl);

      const joinedPlayerId = joined.player_id || joined.id || playerId;
      const joinedPlayer = joined.room_state?.players?.find(
        (player) => player.id === joinedPlayerId,
      );

      setRoomHash(resolvedRoomHash);
      setPlayerId(joinedPlayerId);
      setRole(joinedPlayer?.role || role);
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

  function selectSavedRoom(nextRoomHash) {
    setSelectedSavedRoomId(nextRoomHash);
    setRoomHash(nextRoomHash);
    setNotice(`已选择房间 ${nextRoomHash}，填写用户名和角色名后可以加入。`);
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
      }, serverUrl);
      nextRoomState = created.room_state || created;
    } catch (error) {
      if (error.status === 409) {
        setNotice("房间 ID 已存在，请更换 ID，或从已保存房间列表加入。");
      } else {
        setNotice("创建房间失败，请确认后端状态。");
      }
      setIsBusy(false);
      return;
    }

    try {
      const createdRoomHash = nextRoomState?.room_hash || effectiveRoomId;
      const joined = await roomApi.joinRoom(createdRoomHash, {
        player_name: playerName.trim(),
        character_name: characterName.trim(),
        role: "host",
      }, serverUrl);

      setRoomHash(createdRoomHash);
      setPlayerId(joined.player_id || joined.id || "player_001");
      setRoomState((current) =>
        mergeRoomState(
          mergeRoomState(current, nextRoomState),
          joined.room_state || {
            room_id: effectiveRoomId,
            room_hash: createdRoomHash,
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
      setNotice("创建或加入房间失败，未进入本地演示房间。");
    } finally {
      setIsBusy(false);
    }
  }

  function resetToMainMenu(nextNotice) {
    setScreen("main");
    setSocketStatus("closed");
    setActionText("");
    setHostNote("");
    setNotice(nextNotice);
  }

  async function leaveRoom() {
    const leavingRoomId = roomHash;
    const leavingPlayerId = playerId;

    setIsBusy(true);

    try {
      if (leavingRoomId && leavingPlayerId) {
        await roomApi.leaveRoom(leavingRoomId, { player_id: leavingPlayerId }, serverUrl);
      }
      resetToMainMenu("已离开房间。");
    } catch {
      resetToMainMenu("离开房间请求失败，已返回主菜单；请检查后端是否已移除此玩家。");
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
      const state = await roomApi.submitAction(roomHash, payload, serverUrl);
      setRoomState((current) => mergeRoomState(current, state));
      setNotice("行动已提交。");
    } catch {
      setNotice("行动提交失败，房间状态未在本地伪造更新。");
    } finally {
      setIsBusy(false);
    }
  }

  async function toggleReady() {
    const ready = !currentPlayer?.ready;

    if (ready && !actionText.trim()) {
      setNotice("请先输入本回合行动，再提交并准备。");
      return;
    }

    setIsBusy(true);

    try {
      if (ready) {
        const actionPayload = {
          player_id: playerId,
          character_name: currentPlayer?.character_name || characterName,
          action_text: actionText.trim(),
          turn_index: roomState.turn_index,
        };
        const actionState = await roomApi.submitAction(roomHash, actionPayload, serverUrl);
        setRoomState((current) => mergeRoomState(current, actionState));
      }

      const state = await roomApi.updateReady(roomHash, { player_id: playerId, ready }, serverUrl);
      setRoomState((current) => mergeRoomState(current, state));
      setNotice(ready ? "行动已提交，已标记准备。" : "已取消准备。");
    } catch {
      setNotice(ready ? "提交并准备失败，房间状态未在本地伪造更新。" : "取消准备失败，房间状态未在本地伪造更新。");
    } finally {
      setIsBusy(false);
    }
  }

  async function resolveTurn() {
    setIsBusy(true);

    try {
      const state = await roomApi.resolveTurn({
        room_hash: roomHash,
        host_note: hostNote,
        force: readyCount < roomState.players.length,
      }, serverUrl);

      setRoomState((current) => mergeRoomState(current, state));
      setNotice("本回合已结算。");
    } catch {
      setNotice("回合结算请求失败，未写入本地伪记录。");
    } finally {
      setIsBusy(false);
    }
  }

  async function rollbackTurn() {
    setIsBusy(true);

    try {
      const state = await roomApi.rollback({
        room_hash: roomHash,
        turn_index: Math.max(1, roomState.turn_index - 1),
      }, serverUrl);

      setRoomState((current) => mergeRoomState(current, state));
      setNotice("已回滚到上一回合。");
    } catch {
      setNotice("回滚失败，房间状态未在本地伪造更新。");
    } finally {
      setIsBusy(false);
    }
  }

  if (screen === "main") {
    return (
      <MainMenu
        serverUrl={serverUrl}
        setServerUrl={setServerUrl}
        roomId={roomHash}
        setRoomId={setRoomHash}
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
        savedRooms={savedRooms}
        savedRoomsStatus={savedRoomsStatus}
        selectedSavedRoomId={selectedSavedRoomId}
        isLoadingSavedRooms={isLoadingSavedRooms}
        onSelectSavedRoom={selectSavedRoom}
        onRefreshSavedRooms={loadSavedRooms}
        themeClass={themeClass}
        themeStyle={themeStyle}
        themeSwitcher={themeSwitcher}
      />
    );
  }

  if (screen === "create") {
    return (
      <CreateRoomMenu
        serverUrl={serverUrl}
        setServerUrl={setServerUrl}
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
        themeClass={themeClass}
        themeStyle={themeStyle}
        themeSwitcher={themeSwitcher}
      />
    );
  }

  return (
    <main className={`app-shell ${themeClass}`} style={themeStyle}>
      {themeSwitcher}
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
            serverUrl={serverUrl}
            roomId={roomId}
            playerName={playerName}
            characterName={characterName}
            role={role}
            worldTitle={roomState.world?.title || worldTitle}
            turnIndex={roomState.turn_index}
            onLeave={leaveRoom}
            isBusy={isBusy}
          />

          <PlayerList players={roomState.players} />
          <WorldPanel world={roomState.world} />
          <CharacterPanel characters={roomState.characters} />
        </aside>

        <section className="main-stage">
          <section className="scene-panel">
            <div className="scene-meta">
              <StatusPill>{roomState.scene.time}</StatusPill>
              <StatusPill>{roomState.scene.location}</StatusPill>
            </div>
            <h2>{roomState.scene.location}</h2>
            <MarkdownText text={roomState.scene.description} fallback="暂无场景描述。" />
          </section>

          <section className="panel latest-action-panel">
            <div className="panel-heading">
              <h2>最新行动记录</h2>
              <StatusPill>{latestTimelineEvent?.timestamp || "暂无"}</StatusPill>
            </div>
            <strong>{latestTimelineEvent?.title || latestTimelineEvent?.type || "暂无记录"}</strong>
            <MarkdownText text={latestTimelineText} fallback="当前还没有回合结算记录。" />
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
                <button type="button" onClick={toggleReady} disabled={isBusy}>
                  {currentPlayer?.ready ? "取消准备" : "提交并准备"}
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
