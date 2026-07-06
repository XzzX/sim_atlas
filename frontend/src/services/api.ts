import axios from "axios";
import {
  type ArtifactResponse,
  ArtifactResponseSchema,
  type ScoredSearchResponse,
  ScoredSearchResponseSchema,
  type Filter,
  type FilterOptions,
  FilterOptionsSchema,
  type ExecutionResultMetadata,
  ExecutionResultListSchema,
} from "../types/index";

const API_BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const simAtlasAPI = {
  getNode: async (nodeHash: string): Promise<ArtifactResponse> => {
    const response = await api.get(`/artifacts/${nodeHash}`);
    return ArtifactResponseSchema.parse(response.data);
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
};

export default api;
