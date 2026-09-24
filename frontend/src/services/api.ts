import axios from "axios";
import {
  type NodeResponse,
  NodeResponseSchema,
  type ScoredSearchResponse,
  ScoredSearchResponseSchema,
  type Filter,
  type FilterOptions,
  FilterOptionsSchema,
  type ExecutionResultMetadata,
  ExecutionResultListSchema,
  type NodeSuggestion,
  NodeSuggestionListSchema,
} from "../types/index";

const API_BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const simAtlasAPI = {
  getNode: async (nodeHash: string): Promise<NodeResponse> => {
    const response = await api.get(`/artifacts/${nodeHash}`);
    return NodeResponseSchema.parse(response.data);
  },

  getFilterOptions: async (): Promise<FilterOptions> => {
    const response = await api.get("/filter_options");
    return FilterOptionsSchema.parse(response.data);
  },

  getExecutionResults: async (artifactId: string): Promise<ExecutionResultMetadata[]> => {
    const response = await api.get(`/artifacts/${artifactId}/execution_results`);
    return ExecutionResultListSchema.parse(response.data);
  },

  search: async (
    query: string | null,
    filterOptions: Filter,
    page = 1,
    limit = 10,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post("/search", {
      query,
      filter: filterOptions,
      page,
      limit,
    });
    return ScoredSearchResponseSchema.parse(response.data);
  },

  // Fast type-ahead lookup for the search-as-you-type dropdown — matches only
  // name/import path, honours the same filters as `search`, no enrichment.
  // See ADR-0020.
  suggest: async (
    query: string,
    filterOptions: Filter,
    limit = 8,
  ): Promise<NodeSuggestion[]> => {
    const response = await api.post("/suggest", {
      query,
      filter: filterOptions,
      limit,
    });
    return NodeSuggestionListSchema.parse(response.data);
  },
};

export default api;
