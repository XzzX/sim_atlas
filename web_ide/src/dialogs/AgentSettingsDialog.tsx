import * as React from "react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import type { LLMProviderInfo } from "../interfaces/BackendSchema";
import { ReasoningEffortSchema } from "../interfaces/BackendSchema";
import type { AgentSettings } from "../lib/agentSettings";

/**
 * Unlike the other dialogs in this directory there is no `isOpen` prop: the
 * caller mounts this component only while it is open, so the form seeds itself
 * from `settings` on mount and a cancelled edit cannot linger.
 */
interface AgentSettingsDialogProps {
  onClose: () => void;
  /** Providers the server allows the agent to be pointed at. */
  providers: LLMProviderInfo[];
  /** Provider the server preselects; null when it has no preference. */
  defaultProvider: string | null;
  /** Reasoning-effort values the server accepts. */
  reasoningEfforts: string[];
  settings: AgentSettings | null;
  onSave: (settings: AgentSettings) => void;
  onClear: () => void;
}

const INPUT_CLASS =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

/** Sentinel for "send no reasoning_effort and let the provider decide". */
const EFFORT_DEFAULT = "";

export const AgentSettingsDialog: React.FC<AgentSettingsDialogProps> = ({
  onClose,
  providers,
  defaultProvider,
  reasoningEfforts,
  settings,
  onSave,
  onClear,
}) => {
  // A stored selection is only honoured if the server still offers it: a catalog
  // can change under a browser that has settings from an earlier visit.
  const initialProvider = useMemo(() => {
    const candidates = [settings?.llm_provider, defaultProvider];
    return (
      candidates.find((id) => providers.some((p) => p.id === id)) ??
      providers[0]?.id ??
      ""
    );
  }, [settings?.llm_provider, defaultProvider, providers]);

  const [providerId, setProviderId] = useState(initialProvider);
  const provider = providers.find((p) => p.id === providerId) ?? null;

  const [model, setModel] = useState(() => {
    const stored = settings?.llm_chat_model;
    const initial = providers.find((p) => p.id === initialProvider);
    if (initial === undefined) return "";
    return stored !== undefined && initial.models.some((m) => m.name === stored)
      ? stored
      : initial.default_model;
  });
  const [effort, setEffort] = useState<string>(
    settings?.llm_reasoning_effort ?? EFFORT_DEFAULT,
  );
  const [apiKey, setApiKey] = useState(settings?.llm_api_key ?? "");

  const selectedModel = provider?.models.find((m) => m.name === model) ?? null;
  const supportsEffort = selectedModel?.supports_reasoning_effort === true;

  const handleProviderChange = useCallback(
    (nextId: string) => {
      setProviderId(nextId);
      // The model list is provider-specific, so a carried-over name would be
      // rejected by the server.
      setModel(providers.find((p) => p.id === nextId)?.default_model ?? "");
    },
    [providers],
  );

  // Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [onClose]);

  const handleSave = useCallback(() => {
    const parsedEffort = ReasoningEffortSchema.safeParse(effort);
    onSave({
      llm_api_key: apiKey.trim(),
      llm_provider: providerId,
      llm_chat_model: model,
      // Omitted unless the model actually accepts it, so a stale choice cannot
      // be sent to a model that would reject it.
      ...(supportsEffort && parsedEffort.success
        ? { llm_reasoning_effort: parsedEffort.data }
        : {}),
    });
    onClose();
  }, [
    apiKey,
    providerId,
    model,
    effort,
    supportsEffort,
    onSave,
    onClose,
  ]);

  const handleClear = useCallback(() => {
    onClear();
    onClose();
  }, [onClear, onClose]);

  const needsKey = provider?.requires_api_key !== false;
  const canSave =
    provider !== null && model !== "" && (!needsKey || apiKey.trim() !== "");

  return (
    <div
      className="fixed inset-0 bg-black/50 flex justify-center items-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-background text-foreground border border-border rounded-lg shadow-md p-6 max-w-md w-11/12 flex flex-col gap-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">Agent settings</h2>
          <p className="text-xs text-muted-foreground">
            The agent runs on your own API key. It is stored in this browser,
            sent with each agent request, and never stored on the server.
          </p>
        </div>

        {providers.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            This server has no LLM providers configured, so the agent cannot
            run. Ask the administrator to set{" "}
            <code className="text-xs">llm_providers</code>.
          </p>
        ) : (
          <>
            <div className="space-y-1">
              <label
                htmlFor="agent-provider"
                className="text-xs font-medium text-muted-foreground"
              >
                Provider
              </label>
              <select
                id="agent-provider"
                value={providerId}
                onChange={(e) => handleProviderChange(e.target.value)}
                className={INPUT_CLASS}
              >
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-muted-foreground break-all">
                Your key is sent to {provider?.base_url}
              </p>
            </div>

            <div className="space-y-1">
              <label
                htmlFor="agent-model"
                className="text-xs font-medium text-muted-foreground"
              >
                Model
              </label>
              <select
                id="agent-model"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className={INPUT_CLASS}
              >
                {provider?.models.map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label
                htmlFor="agent-effort"
                className="text-xs font-medium text-muted-foreground"
              >
                Reasoning effort
              </label>
              <select
                id="agent-effort"
                value={supportsEffort ? effort : EFFORT_DEFAULT}
                onChange={(e) => setEffort(e.target.value)}
                className={`${INPUT_CLASS} disabled:opacity-50`}
                disabled={!supportsEffort}
              >
                <option value={EFFORT_DEFAULT}>Provider default</option>
                {reasoningEfforts.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
              {!supportsEffort && (
                <p className="text-xs text-muted-foreground">
                  This model does not accept a reasoning effort.
                </p>
              )}
            </div>

            {needsKey && (
              <div className="space-y-1">
                <label
                  htmlFor="agent-api-key"
                  className="text-xs font-medium text-muted-foreground"
                >
                  API key
                </label>
                <input
                  id="agent-api-key"
                  type="password"
                  autoComplete="off"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className={INPUT_CLASS}
                  autoFocus
                />
              </div>
            )}
          </>
        )}

        <div className="flex gap-2 justify-end">
          {settings !== null && (
            <Button variant="ghost" onClick={handleClear}>
              Clear
            </Button>
          )}
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          {providers.length > 0 && (
            <Button onClick={handleSave} disabled={!canSave}>
              Save
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
