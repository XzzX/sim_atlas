import { z } from "zod";

const STORAGE_KEY = "simflow.agentSettings";

/**
 * Per-user LLM credentials for the agent.
 *
 * The backend requires both fields together, so they are always read and
 * written as a pair. The provider base URL is not included: it is fixed by the
 * server and reported via `/capabilities`.
 */
export const AgentSettingsSchema = z.object({
  llm_api_key: z.string().min(1),
  llm_chat_model: z.string().min(1),
});
export type AgentSettings = z.infer<typeof AgentSettingsSchema>;

/** Returns the stored settings, or null when absent, unreadable or malformed. */
export function loadAgentSettings(): AgentSettings | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    return AgentSettingsSchema.parse(JSON.parse(raw));
  } catch {
    // A stale or corrupt entry degrades to "not configured" rather than
    // breaking the panel on mount.
    return null;
  }
}

export function saveAgentSettings(settings: AgentSettings): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
}

export function clearAgentSettings(): void {
  localStorage.removeItem(STORAGE_KEY);
}
