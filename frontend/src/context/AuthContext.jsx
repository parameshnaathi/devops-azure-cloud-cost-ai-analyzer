import { createContext, useContext, useMemo, useState, useCallback } from "react";
import { api } from "../api";

const AuthContext = createContext(null);

const STORAGE_KEY = "cost-detective-auth";

function loadStoredAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadStoredAuth);

  const persist = useCallback((value) => {
    setAuth(value);
    if (value) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  }, []);

  const signup = useCallback(
    async (email, password) => {
      const result = await api.signup(email, password);
      persist({ token: result.access_token, user: result.user });
      return result;
    },
    [persist]
  );

  const login = useCallback(
    async (email, password) => {
      const result = await api.login(email, password);
      persist({ token: result.access_token, user: result.user });
      return result;
    },
    [persist]
  );

  const logout = useCallback(() => persist(null), [persist]);

  const value = useMemo(
    () => ({
      token: auth?.token ?? null,
      user: auth?.user ?? null,
      isAuthenticated: Boolean(auth?.token),
      signup,
      login,
      logout,
    }),
    [auth, signup, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
