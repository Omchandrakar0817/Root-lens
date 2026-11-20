const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
const localHost = typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname);
export const API_URL = configuredApiUrl || (localHost
  ? `http://${window.location.hostname}:8000/api/v1`
  : "/api/v1");

export type Session = { access_token: string; refresh_token: string; user: User };
export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
  notify_email: boolean;
  theme: string;
};

export function loadSession(): Session | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem("incident_rca_session");
  return raw ? (JSON.parse(raw) as Session) : null;
}

export function saveSession(session: Session) {
  sessionStorage.setItem("incident_rca_session", JSON.stringify(session));
}

export function clearSession() {
  sessionStorage.removeItem("incident_rca_session");
}

let refreshPromise: Promise<Session | null> | null = null;

async function refreshSession(refreshToken: string): Promise<Session | null> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_URL}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!response.ok) return null;
        const next = (await response.json()) as Session;
        saveSession(next);
        return next;
      } catch {
        return null;
      }
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

export async function api<T>(path: string, options: RequestInit = {}, retry = true): Promise<T> {
  const session = loadSession();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (session?.access_token) headers.set("Authorization", `Bearer ${session.access_token}`);
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("Cannot reach the monitoring API. Check that the backend is running and NEXT_PUBLIC_API_URL is correct.");
  }
  if (response.status === 401 && retry && session?.refresh_token && !path.startsWith("/auth/login")) {
    const next = await refreshSession(session.refresh_token);
    if (next) {
      return api<T>(path, options, false);
    }
    clearSession();
    if (typeof window !== "undefined") window.location.assign("/login");
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      detail = response.statusText;
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function logoutSession() {
  const session = loadSession();
  if (session) {
    try {
      await api("/auth/logout", { method: "POST", body: JSON.stringify({ refresh_token: session.refresh_token }) });
    } catch {
      /* revoke locally even if the API is unreachable */
    }
  }
  clearSession();
}
