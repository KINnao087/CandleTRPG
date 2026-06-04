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
    const error = new Error(message || `Request failed: ${response.status}`);
    error.status = response.status;
    throw error;
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const roomApi = {
  getSavedRooms(serverUrl) {
    return request("/api/saved-rooms", { serverUrl });
  },

  createRoom(roomId, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  getState(roomHash, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomHash)}/state`, { serverUrl });
  },

  importWorld(roomHash, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomHash)}/world`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  joinRoom(roomHash, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomHash)}/join`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  leaveRoom(roomHash, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomHash)}/leave`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  submitAction(roomHash, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomHash)}/actions`, {
      method: "POST",
      body: JSON.stringify(payload),
      serverUrl,
    });
  },

  updateReady(roomHash, payload, serverUrl) {
    return request(`/api/rooms/${encodeURIComponent(roomHash)}/ready`, {
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
