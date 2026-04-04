/**
 * FinBot API Client
 * Handles all communication with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface UserInfo {
  id: number;
  username: string;
  role: string;
  department: string;
  accessible_collections: string[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: UserInfo;
}

export interface SourceCitation {
  document: string;
  page?: number;
  section?: string;
  chunk_type?: string;
}

export interface GuardrailInfo {
  triggered: boolean;
  type?: string;
  reason?: string;
}

export interface ChatResponse {
  answer: string;
  route?: string;
  sources: SourceCitation[];
  guardrail?: GuardrailInfo;
  user_role: string;
  accessible_collections: string[];
  blocked: boolean;
}

// ---------------------------------------------------------------------------
// Token Management
// ---------------------------------------------------------------------------

let authToken: string | null = null;

export function setToken(token: string) {
  authToken = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("finbot_token", token);
  }
}

export function getToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("finbot_token");
  }
  return authToken;
}

export function clearToken() {
  authToken = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("finbot_token");
    localStorage.removeItem("finbot_user");
  }
}

// ---------------------------------------------------------------------------
// API Helpers
// ---------------------------------------------------------------------------

async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error: ${res.status}`);
  }

  return res.json();
}

// ---------------------------------------------------------------------------
// Auth API
// ---------------------------------------------------------------------------

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const data = await apiFetch("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setToken(data.access_token);
  if (typeof window !== "undefined") {
    localStorage.setItem("finbot_user", JSON.stringify(data.user));
  }
  return data;
}

export async function getMe(): Promise<UserInfo> {
  return apiFetch("/api/user/me");
}

// ---------------------------------------------------------------------------
// Chat API
// ---------------------------------------------------------------------------

export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  return apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId }),
  });
}

// ---------------------------------------------------------------------------
// Admin API
// ---------------------------------------------------------------------------

export async function adminListUsers(): Promise<{ users: UserInfo[] }> {
  return apiFetch("/api/admin/users");
}

export async function adminCreateUser(
  username: string,
  password: string,
  role: string,
  department: string
): Promise<{ message: string; user_id: number }> {
  return apiFetch("/api/admin/users", {
    method: "POST",
    body: JSON.stringify({ username, password, role, department }),
  });
}

export async function adminUpdateRole(
  userId: number,
  role: string
): Promise<{ message: string }> {
  return apiFetch(`/api/admin/users/${userId}/role`, {
    method: "PUT",
    body: JSON.stringify({ role }),
  });
}

export async function adminDeleteUser(
  userId: number
): Promise<{ message: string }> {
  return apiFetch(`/api/admin/users/${userId}`, {
    method: "DELETE",
  });
}
