export const DEFAULT_API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export function normalizeApiBaseUrl(serverUrl = DEFAULT_API_BASE_URL) {
  const rawUrl = (serverUrl || "").trim().replace(/\/+$/, "");
  if (!rawUrl) {
    return "";
  }
  if (/^https?:\/\//i.test(rawUrl)) {
    return rawUrl;
  }
  return `http://${rawUrl}`;
}

async function request(path, options = {}) {
  const { serverUrl, ...fetchOptions } = options;
  const baseUrl = normalizeApiBaseUrl(serverUrl);

  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(fetchOptions.headers || {}),
    },
    ...fetchOptions,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const roomApi = {
  createRoom(roomId, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  getState(roomId, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/state`, { serverUrl });
  },

  importWorld(roomId, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/world`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  joinRoom(roomId, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/join`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  leaveRoom(roomId, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/leave`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  submitAction(roomId, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/actions`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  updateReady(roomId, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/ready`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  resolveTurn(payload, serverUrl) {
    return request("/api/host/resolve-turn", {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  rollback(payload, serverUrl) {
    return request("/api/host/rollback", {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },
};
