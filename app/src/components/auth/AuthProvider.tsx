import { useState, useEffect, useCallback, type ReactNode } from 'react';
import {
  AuthContext,
  type AuthUser,
  authFetch,
  storeSession,
  clearSession,
  getStoredToken,
  getStoredUser,
} from '@/lib/auth';

interface TokenResponse {
  access_token: string;
  token_type: string;
  user_id: string;
  email: string;
  name?: string | null;
  is_admin?: boolean;
  email_verified?: boolean;
  effective_plan?: string;
  billing_enabled?: boolean;
}

export default function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(getStoredToken);
  const [user, setUser] = useState<AuthUser | null>(getStoredUser);
  const [isLoaded, setIsLoaded] = useState(false);

  // On mount, verify the stored token is still valid by hitting /users/me.
  // IMPORTANT: Only force-logout on genuine auth failures (401).
  // Server errors (500, network down, etc.) must NOT log out the user —
  // we keep the stored session and let the user land in the dashboard.
  useEffect(() => {
    const stored = getStoredToken();
    if (!stored) {
      setIsLoaded(true);
      return;
    }
    const tok = stored;
    fetch('/api/v1/users/me', {
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${tok}` },
    })
      .then(async (res) => {
        if (res.ok) {
          const u = await res.json() as AuthUser;
          setUser(u);
          setToken(tok);
        } else if (res.status === 401 || res.status === 403) {
          // Genuine auth failure — token is invalid/expired
          clearSession();
          setToken(null);
          setUser(null);
        }
        // For any other status (500, 502, 503, etc.): keep existing session.
        // The stored user data is still valid; server may be temporarily down.
      })
      .catch(() => {
        // Network error — keep existing session so the user is not logged out
        // during transient outages or server restarts.
      })
      .finally(() => setIsLoaded(true));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await authFetch<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    const u: AuthUser = { id: data.user_id, email: data.email, name: data.name, isAdmin: data.is_admin, emailVerified: data.email_verified, effectivePlan: data.effective_plan, billingEnabled: data.billing_enabled };
    storeSession(data.access_token, u);
    setToken(data.access_token);
    setUser(u);
  }, []);

  const register = useCallback(async (email: string, password: string, name?: string) => {
    const data = await authFetch<TokenResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password, name: name || undefined }),
    });
    const u: AuthUser = { id: data.user_id, email: data.email, name: data.name, isAdmin: data.is_admin, emailVerified: data.email_verified, effectivePlan: data.effective_plan, billingEnabled: data.billing_enabled };
    storeSession(data.access_token, u);
    setToken(data.access_token);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        isAuthenticated: !!token && !!user,
        isLoaded,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
