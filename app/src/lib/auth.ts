/**
 * AmarktAI Marketing — App-owned JWT Auth
 *
 * Stores the token in localStorage under "amarktai_token".
 * The AuthContext provides isAuthenticated, user, login, register, logout.
 */

import { createContext, useContext } from 'react';

const TOKEN_KEY = 'amarktai_token';
const USER_KEY = 'amarktai_user';

export interface AuthUser {
  id: string;
  email: string;
  name?: string | null;
  isAdmin?: boolean;
  emailVerified?: boolean;
  effectivePlan?: string;
  billingEnabled?: boolean;
}

export interface AuthState {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoaded: boolean;
}

export interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => void;
}

// ── Token persistence helpers ─────────────────────────────────────────────

export function getStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

export function storeSession(token: string, user: AuthUser): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

// ── API helper (adds auth header automatically) ───────────────────────────

const BASE = '/api/v1';

export async function authFetch<T>(
  path: string,
  init?: RequestInit,
  token?: string | null,
): Promise<T> {
  const tok = token ?? getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string>),
  };
  if (tok) headers['Authorization'] = `Bearer ${tok}`;

  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body?.detail ?? detail;
    } catch {
      // ignore parse error
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── React context (default = unauthenticated) ─────────────────────────────

export const AuthContext = createContext<AuthContextValue>({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoaded: false,
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}
