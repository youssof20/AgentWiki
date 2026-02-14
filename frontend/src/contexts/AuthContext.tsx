import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { AGENT_ID_STORAGE_KEY, postRegister, type RegisterRequest } from "@/lib/api";

interface AuthContextValue {
  agentId: string | null;
  isLoading: boolean;
  login: (id: string) => void;
  logout: () => void;
  register: (body: RegisterRequest) => Promise<string>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [agentId, setAgentIdState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(AGENT_ID_STORAGE_KEY);
      setAgentIdState(stored && stored.trim() ? stored.trim() : null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const setAgentId = useCallback((id: string | null) => {
    if (id?.trim()) {
      localStorage.setItem(AGENT_ID_STORAGE_KEY, id.trim());
      setAgentIdState(id.trim());
    } else {
      localStorage.removeItem(AGENT_ID_STORAGE_KEY);
      setAgentIdState(null);
    }
  }, []);

  const login = useCallback(
    (id: string) => {
      if (id?.trim()) setAgentId(id.trim());
    },
    [setAgentId]
  );

  const logout = useCallback(() => {
    setAgentId(null);
  }, [setAgentId]);

  const register = useCallback(async (body: RegisterRequest): Promise<string> => {
    const res = await postRegister(body);
    setAgentId(res.agent_id);
    return res.agent_id;
  }, [setAgentId]);

  const value: AuthContextValue = {
    agentId,
    isLoading,
    login,
    logout,
    register,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
