import { z } from "zod";
import { ReasoningEffortSchema } from "../interfaces/BackendSchema";

const STORAGE_KEY = "simflow.agentSettings";

/**
 * Per-user LLM credentials and provider choice for the agent.
 *
 * `llm_provider` is an opaque id from `/capabilities`, never a URL: the server
 * resolves it against its own allowlist, so a value edited here cannot point the
 * agent anywhere the operator has not permitted. Every field is spread straight
 * into the `AgentRequest` body, so this shape must stay a subset of
 * `AgentRequestSchema`.
 *
 * The selection fields are optional so an entry written before they existed still
 * loads; the server then falls back to its own defaults. Extra keys left over
 * from an earlier version of this shape are dropped on read.
 */
export const AgentSettingsSchema = z.object({
  llm_api_key: z.string().min(1),
  llm_provider: z.string().min(1).optional(),
  llm_chat_model: z.string().min(1).optional(),
  llm_reasoning_effort: ReasoningEffortSchema.optional(),
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
