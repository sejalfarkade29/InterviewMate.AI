"use client";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, ApiError } from "@/lib/api";
import { clearLocalSession } from "@/lib/localStore";
import type { User } from "@/types";

type AuthState = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUserName: (name: string) => void;
};
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 401 simply means "not signed in". Any other failure (backend down) also lands on the login page,
    // where signing in shows the real error message.
    clearLocalSession(); // older versions kept a fake offline session; it can no longer reach the backend
    api<User>("/auth/me").then(setUser).catch((e) => { if (!(e instanceof ApiError)) console.error(e); setUser(null); }).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setUser(await api<User>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }));
  }, []);
  const register = useCallback(async (full_name: string, email: string, password: string) => {
    setUser(await api<User>("/auth/register", { method: "POST", body: JSON.stringify({ full_name, email, password }) }));
  }, []);
  const logout = useCallback(async () => {
    try { await api("/auth/logout", { method: "POST" }); } catch { /* signing out locally is enough */ }
    setUser(null);
  }, []);
  const setUserName = useCallback((name: string) => setUser((u) => (u ? { ...u, full_name: name } : u)), []);

  return <AuthContext.Provider value={{ user, loading, login, register, logout, setUserName }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
