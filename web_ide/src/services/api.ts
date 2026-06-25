import axios from "axios";
import {
  ArtifactResponseSchema,
  ScoredSearchResponseSchema,
  FilterOptionsSchema,
  AgentSSEEventSchema,
  type ArtifactResponse,
  type ScoredSearchResponse,
  type Filter,
  type FilterOptions,
  type AgentRequest,
  type AgentSSEEvent,
} from "../interfaces/BackendSchema";

const API_BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const simAtlasAPI = {
  getNode: async (nodeHash: string): Promise<ArtifactResponse> => {
    const response = await api.get(`/nodes/${nodeHash}`);
    return ArtifactResponseSchema.parse(response.data);
  },

  getFilterOptions: async (): Promise<FilterOptions> => {
    const response = await api.get("/filter_options");
    return FilterOptionsSchema.parse(response.data);
  },

  search: async (
    query: string | null,
    filterOptions: Filter | null,
    page = 1,
    limit = 20,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post(
      "/search",
      { ...filterOptions },
      {
        params: { query, page, limit },
      },
    );
    return ScoredSearchResponseSchema.parse(response.data);
  },

  semanticSearch: async (
    query: string,
    filterOptions: Filter | null,
    page = 1,
    limit = 20,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post(
      "/semantic_search",
      { ...filterOptions },
      {
        params: { query, page, limit },
      },
    );
    return ScoredSearchResponseSchema.parse(response.data);
  },

  agentStream: async (
    request: AgentRequest,
    onEvent: (event: AgentSSEEvent) => void,
    signal?: AbortSignal,
  ): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/agent/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal,
    });
    if (!response.ok) {
      throw new Error(`Agent stream error: ${response.status}`);
    }
    const reader = response.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data: ")) continue;
        try {
          const parsed = AgentSSEEventSchema.parse(JSON.parse(line.slice(6)));
          onEvent(parsed);
        } catch {
          console.error("Failed to parse SSE event:", line);
        }
      }
    }
  },
};

export default api;
