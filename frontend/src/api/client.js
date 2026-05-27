const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
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
  createRoom(roomId, payload) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getState(roomId) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/state`);
  },

  importWorld(roomId, payload) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/world`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  joinRoom(roomId, payload) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/join`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  submitAction(roomId, payload) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/actions`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateReady(roomId, payload) {
    return request(`/api/rooms/${encodeURIComponent(roomId)}/ready`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  resolveTurn(payload) {
    return request("/api/host/resolve-turn", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  rollback(payload) {
    return request("/api/host/rollback", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};
