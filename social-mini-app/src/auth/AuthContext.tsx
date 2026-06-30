import { retrieveLaunchParams } from "@telegram-apps/sdk";
import { type ReactNode, createContext, useCallback, useEffect, useRef, useState } from "react";
import { apiPost, setAuthToken } from "../api/client";

const STORAGE_KEY = "social_intel_jwt";

export type UserRole = "user" | "admin";

export interface AuthUser {
  id: number;
  first_name: string;
  last_name?: string | null;
  username?: string | null;
  role: UserRole;
}

export interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  isAdmin: boolean;
  login: () => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

interface TelegramLoginResponse {
  token: string;
  user: AuthUser;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const login = useCallback(async () => {
    let initDataRaw: string | null = null;
    try {
      const lp = retrieveLaunchParams();
      initDataRaw = lp.initDataRaw ?? null;
    } catch {
      /* running outside Telegram */
    }

    if (!initDataRaw) {
      if (import.meta.env.VITE_TELEGRAM_AUTH_REQUIRED === "true") {
        if (mountedRef.current) {
          setError("This app must be opened inside Telegram.");
          setIsLoading(false);
        }
        return;
      }
      /* Outside Telegram — use static API key fallback. No JWT needed. */
      setAuthToken(null);
      if (mountedRef.current) {
        setIsLoading(false);
      }
      return;
    }

    try {
      const res = await apiPost<TelegramLoginResponse>("/v1/auth/telegram-login", {
        init_data: initDataRaw,
      });

      if (!mountedRef.current) return;

      setToken(res.token);
      setUser(res.user);
      setAuthToken(res.token);
      localStorage.setItem(STORAGE_KEY, res.token);
    } catch (err) {
      if (!mountedRef.current) return;

      const message =
        err instanceof Error ? err.message : "Authentication failed. Please try again.";
      setError(message);
      setAuthToken(null);
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
      }
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    setAuthToken(null);
    localStorage.removeItem(STORAGE_KEY);
    setError(null);
  }, []);

  useEffect(() => {
    /* Try cached JWT first for instant render, then re-auth in background */
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      setToken(cached);
      setAuthToken(cached);
    }
    login();
  }, [login]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        isLoading,
        error,
        isAdmin: user?.role === "admin",
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
