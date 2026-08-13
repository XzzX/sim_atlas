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

const API_BASE_URL = "/api/v1";

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
    limit = 20,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post("/search", {
      query,
      filter: filterOptions,
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
      // The backend rejects a non-allowlisted provider/model or a missing key
      // with a 400 whose `detail` says what is allowed — without it the user
      // sees only a bare status code.
      const detail = await response
        .json()
        .then((body: unknown) =>
          typeof body === "object" &&
          body !== null &&
          typeof (body as { detail?: unknown }).detail === "string"
            ? (body as { detail: string }).detail
            : null,
        )
        .catch(() => null);
      throw new Error(
        detail !== null
          ? `Agent stream error: ${detail}`
          : `Agent stream error: ${response.status}`,
      );
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
