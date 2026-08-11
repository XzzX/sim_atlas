import * as React from "react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import type { AgentSettings } from "../lib/agentSettings";

/**
 * Unlike the other dialogs in this directory there is no `isOpen` prop: the
 * caller mounts this component only while it is open, so the form seeds itself
 * from `settings` on mount and a cancelled edit cannot linger.
 */
interface AgentSettingsDialogProps {
  onClose: () => void;
  /** Provider URL fixed by the server; null when none is configured. */
  baseUrl: string | null;
  settings: AgentSettings | null;
  onSave: (settings: AgentSettings) => void;
  onClear: () => void;
}

const INPUT_CLASS =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring";

export const AgentSettingsDialog: React.FC<AgentSettingsDialogProps> = ({
  onClose,
  baseUrl,
  settings,
  onSave,
  onClear,
}) => {
  const [apiKey, setApiKey] = useState(settings?.llm_api_key ?? "");
  const [model, setModel] = useState(settings?.llm_chat_model ?? "");

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
    onSave({ llm_api_key: apiKey.trim(), llm_chat_model: model.trim() });
    onClose();
  }, [apiKey, model, onSave, onClose]);

  const handleClear = useCallback(() => {
    onClear();
    onClose();
  }, [onClear, onClose]);

  // Both fields must travel together — the backend rejects a half-filled pair.
  const canSave = apiKey.trim() !== "" && model.trim() !== "";

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
            Use your own LLM credentials for this browser. They are sent with
            each agent request and never stored on the server.
          </p>
        </div>

        {baseUrl == null ? (
          <p className="text-sm text-muted-foreground">
            This server has no LLM provider configured, so your own key cannot
            be used. Ask the administrator to set{" "}
            <code className="text-xs">llm_base_url</code>.
          </p>
        ) : (
          <>
            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground">
                Provider
              </span>
              <p className="text-sm break-all">{baseUrl}</p>
              <p className="text-xs text-muted-foreground">
                Set by the server — your key must be valid for this provider.
              </p>
            </div>

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

            <div className="space-y-1">
              <label
                htmlFor="agent-model"
                className="text-xs font-medium text-muted-foreground"
              >
                Model
              </label>
              <input
                id="agent-model"
                type="text"
                autoComplete="off"
                placeholder="e.g. qwen3.5-27b"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className={INPUT_CLASS}
              />
            </div>
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
          {baseUrl != null && (
            <Button onClick={handleSave} disabled={!canSave}>
              Save
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
