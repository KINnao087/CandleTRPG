const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function buildWsUrl(roomId, playerId) {
  const base = API_BASE_URL || window.location.origin;
  const url = new URL(base, window.location.origin);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `/ws/rooms/${encodeURIComponent(roomId)}`;

  if (playerId) {
    url.searchParams.set("player_id", playerId);
  }

  return url.toString();
}

export function createRoomSocket({ roomId, playerId, onMessage, onStatus }) {
  if (!roomId) {
    return null;
  }

  const socket = new WebSocket(buildWsUrl(roomId, playerId));

  socket.addEventListener("open", () => {
    onStatus?.("connected");
    socket.send(JSON.stringify({
      type: "join_room",
      room_id: roomId,
      player_id: playerId,
      payload: {},
      timestamp: new Date().toISOString(),
    }));
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
