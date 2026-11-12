import axios from "axios";
import {
  type NodeResponse,
  NodeResponseSchema,
  type ScoredSearchResponse,
  ScoredSearchResponseSchema,
  type SearchRequest,
  type SuggestRequest,
  type Filter,
  type FilterOptions,
  FilterOptionsSchema,
  type ExecutionResultMetadata,
  ExecutionResultMetadataSchema,
  type Suggestion,
  SuggestionSchema,
} from "sim-atlas-api-schema";
import { z } from "zod";

const API_BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const simAtlasAPI = {
  getNode: async (nodeHash: string): Promise<NodeResponse> => {
    const response = await api.get(`/nodes/${nodeHash}`);
    return NodeResponseSchema.parse(response.data);
  },

  getFilterOptions: async (): Promise<FilterOptions> => {
    const response = await api.get("/filter_options");
    return FilterOptionsSchema.parse(response.data);
  },

  getExecutionResults: async (nodeId: string): Promise<ExecutionResultMetadata[]> => {
    const response = await api.get(`/nodes/${nodeId}/execution_results`);
    return z.array(ExecutionResultMetadataSchema).parse(response.data);
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
    } satisfies SearchRequest);
    return ScoredSearchResponseSchema.parse(response.data);
  },

  // Fast type-ahead lookup for the search-as-you-type dropdown — matches only
  // name/import path, honours the same filters as `search`, no enrichment.
  // See ADR-0020.
  suggest: async (
    query: string,
    filterOptions: Filter,
    limit = 8,
  ): Promise<Suggestion[]> => {
    const response = await api.post("/suggest", {
      query,
      filter: filterOptions,
      limit,
    } satisfies SuggestRequest);
    return z.array(SuggestionSchema).parse(response.data);
  },
};

export default api;
