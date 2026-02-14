/**
 * AgentWiki backend API client.
 * Backend: POST /inference, GET /health, POST /auth/register. See AgentWiki/api.py.
 */

const DEFAULT_API_URL = "http://localhost:8000";

export const AGENT_ID_STORAGE_KEY = "agentwiki_agent_id";

export function getApiBaseUrl(): string {
  const url = import.meta.env.VITE_AGENTWIKI_API_URL;
  return (typeof url === "string" && url.trim()) ? url.trim() : DEFAULT_API_URL;
}

function buildHeaders(agentId?: string | null): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (agentId?.trim()) headers["X-Agent-ID"] = agentId.trim();
  return headers;
}

/** Single run result (static or AgentWiki). */
export interface RunResult {
  output: string;
  plan: string;
  retry_count: number;
  time_seconds: number;
  score: number | null;
  cards_used?: number;
  cards_used_ids?: string[];
}

/** Response from POST /inference. */
export interface InferenceResponse {
  run_static: RunResult | null;
  run_agentwiki: RunResult | null;
  scores: { static?: number; agentwiki?: number };
  delta: number;
  error: string | null;
  task: string | null;
}

export interface HealthResponse {
  status: string;
}

export async function getHealth(): Promise<HealthResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json() as Promise<HealthResponse>;
}

export interface RegisterRequest {
  agent_name: string;
  team_name?: string;
  email?: string;
}

export interface RegisterResponse {
  agent_id: string;
}

export async function postRegister(
  body: RegisterRequest,
  agentId?: string | null
): Promise<RegisterResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/auth/register`, {
    method: "POST",
    headers: buildHeaders(agentId),
    body: JSON.stringify({
      agent_name: (body.agent_name || "").trim(),
      team_name: (body.team_name || "").trim() || undefined,
      email: (body.email || "").trim() || undefined,
    }),
  });
  const data = (await res.json()) as RegisterResponse & { detail?: string };
  if (!res.ok) {
    const msg =
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
          ? (data.detail as unknown[]).map((x) => String(x)).join(" ")
          : `Registration failed: ${res.status}`;
    throw new Error(msg);
  }
  if (!data.agent_id) throw new Error("No agent_id in response");
  return data;
}

export async function postInference(
  task: string,
  writeBack = true,
  agentId?: string | null
): Promise<InferenceResponse> {
  const base = getApiBaseUrl();
  const res = await fetch(`${base}/inference`, {
    method: "POST",
    headers: buildHeaders(agentId),
    body: JSON.stringify({ task: task.trim(), write_back: writeBack }),
  });
  const data = (await res.json()) as InferenceResponse & { detail?: string };
  if (!res.ok) {
    const msg =
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
          ? (data.detail as unknown[]).map((x) => String(x)).join(" ")
          : data?.error ?? `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return data;
}
