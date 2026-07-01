import axios from "axios";
import {
  ArtifactResponseSchema,
  ScoredSearchResponseSchema,
  FilterOptionsSchema,
  AgentSSEEventSchema,
  CapabilitiesResponseSchema,
  type ArtifactResponse,
  type ScoredSearchResponse,
  type Filter,
  type FilterOptions,
  type AgentRequest,
  type AgentSSEEvent,
  type CapabilitiesResponse,
} from "../interfaces/BackendSchema";

// 1. Dynamically get the subpath prefix (e.g., "/app1" or "/app2")
const getDynamicPrefix = () => {
  const segments = window.location.pathname.split('/');
  return segments[1] ? `/${segments[1]}` : '';
};

// 2. Combine the prefix with your absolute API route
const API_BASE_URL = `${getDynamicPrefix()}/api/v1`;

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const simAtlasAPI = {
  getArtifact: async (artifactId: string): Promise<ArtifactResponse> => {
    const response = await api.get(`/artifacts/${artifactId}`);
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
    semantic: boolean | null = null,
    limit = 20,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post("/search", {
      query,
      filter: filterOptions,
      semantic,
      page,
      limit,
    });
    return ScoredSearchResponseSchema.parse(response.data);
  },

  getCapabilities: async (): Promise<CapabilitiesResponse> => {
    const response = await api.get("/capabilities");
    return CapabilitiesResponseSchema.parse(response.data);
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
