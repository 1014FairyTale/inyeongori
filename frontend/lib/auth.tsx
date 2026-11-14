"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, ApiError, getToken, setToken, type Me, type SignupInput, type TokenResponse } from "@/lib/api";

interface AuthState {
  me: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<Me>;
  signup: (input: SignupInput) => Promise<Me>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setMe(null);
      return;
    }
    try {
      setMe(await api<Me>("/auth/me"));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setToken(null);
        setMe(null);
      }
    }
  }, []);

  // 첫 화면에서 저장된 토큰으로 로그인 상태를 복원해요
  useEffect(() => {
    let cancelled = false;
    (async () => {
      let restored: Me | null = null;
      if (getToken()) {
        try {
          restored = await api<Me>("/auth/me");
        } catch (e) {
          // 인증이 실제로 만료된 경우에만 로그아웃해요 (서버가 잠깐 안 될 때는 유지)
          if (e instanceof ApiError && e.status === 401) setToken(null);
        }
      }
      if (!cancelled) {
        setMe(restored);
        setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await api<TokenResponse>("/auth/login", { method: "POST", json: { email, password } });
    setToken(res.access_token);
    setMe(res.me);
    return res.me;
  }, []);

  const signup = useCallback(async (input: SignupInput) => {
    const res = await api<TokenResponse>("/auth/signup", { method: "POST", json: input });
    setToken(res.access_token);
    setMe(res.me);
    return res.me;
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setMe(null);
  }, []);

  const value = useMemo(
    () => ({ me, loading, login, signup, logout, refresh }),
    [me, loading, login, signup, logout, refresh],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth는 AuthProvider 안에서만 쓸 수 있어요");
  return ctx;
}
