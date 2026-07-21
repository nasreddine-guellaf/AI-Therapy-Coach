import type {
  AuthUser,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
} from "@/types/auth";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");
const TOKEN_KEY = "therapy-coach:access-token:v1";

export class AuthError extends Error {
  constructor(
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "AuthError";
  }
}

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function saveAccessToken(token: string): void {
  try {
    window.localStorage.setItem(TOKEN_KEY, token);
  } catch {
    throw new AuthError("Your browser could not save the login session.");
  }
}

export function logout(): void {
  try {
    window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    // The local session is already inaccessible, which is equivalent to logout.
  }
}

export async function registerUser(request: RegisterRequest): Promise<AuthUser> {
  return requestJson<AuthUser>("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
}

export async function loginUser(request: LoginRequest): Promise<LoginResponse> {
  const response = await requestJson<LoginResponse>("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  saveAccessToken(response.access_token);
  return response;
}

export async function getCurrentUser(): Promise<AuthUser> {
  const token = getAccessToken();
  if (!token) throw new AuthError("Authentication required.", 401);
  return requestJson<AuthUser>("/api/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new AuthError("The authentication service could not be reached.");
  }

  if (!response.ok) {
    const fallback =
      response.status === 401
        ? "Invalid email or password."
        : "The authentication request could not be completed.";
    let message = fallback;
    try {
      const body = (await response.json()) as { detail?: string };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      // Keep the safe fallback when the server does not return JSON.
    }
    throw new AuthError(message, response.status);
  }

  return (await response.json()) as T;
}
