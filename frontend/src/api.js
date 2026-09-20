// Small fetch wrapper for talking to the FastAPI backend.

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000";

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, { method = "GET", token, body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      "Could not reach the backend API. Is it running at " + API_BASE_URL + "?",
      0
    );
  }

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const data = isJson ? await response.json().catch(() => null) : null;

  if (!response.ok) {
    const detail = data?.detail || response.statusText || "Request failed.";
    throw new ApiError(detail, response.status);
  }

  return data;
}

export const api = {
  signup: (email, password) =>
    request("/api/auth/signup", { method: "POST", body: { email, password } }),
  login: (email, password) =>
    request("/api/auth/login", { method: "POST", body: { email, password } }),
  getResourceGroups: (token) => request("/api/resource-groups", { token }),
  analyze: (token, resourceGroup, analysisId) =>
    request("/api/analyze", {
      method: "POST",
      token,
      body: { resource_group: resourceGroup, analysis_id: analysisId },
    }),
  getHistory: (token) => request("/api/history", { token }),
};
