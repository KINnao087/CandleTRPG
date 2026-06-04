import { DEFAULT_API_BASE_URL, normalizeApiBaseUrl } from "../api/client.js";

function buildWsUrl(roomHash, playerId, serverUrl) {
  const base = normalizeApiBaseUrl(serverUrl || DEFAULT_API_BASE_URL) || window.location.origin;
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/rooms/${encodeURIComponent(roomHash)}`;

  if (playerId) {
    url.searchParams.set("player_id", playerId);
  }

  return url.toString();
}

export function createRoomSocket({ roomId, playerId, serverUrl, onMessage, onStatus }) {
  if (!roomId) {
    return null;
  }

  const socket = new WebSocket(buildWsUrl(roomId, playerId, serverUrl));

  socket.addEventListener("open", () => {
    onStatus?.("connected");
  });

  socket.addEventListener("message", (event) => {
    try {
      onMessage?.(JSON.parse(event.data));
    } catch {
      onMessage?.({ type: "raw_message", payload: event.data });
    }
  });

  socket.addEventListener("close", () => onStatus?.("closed"));
  socket.addEventListener("error", () => onStatus?.("error"));

  return socket;
}
