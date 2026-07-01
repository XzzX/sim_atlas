import axios from "axios";
import {
  type ArtifactResponse,
  ArtifactResponseSchema,
  type ScoredSearchResponse,
  ScoredSearchResponseSchema,
  type Filter,
  type FilterOptions,
  FilterOptionsSchema,
} from "../types/index";

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
  getNode: async (nodeHash: string): Promise<ArtifactResponse> => {
    const response = await api.get(`/artifacts/${nodeHash}`);
    return ArtifactResponseSchema.parse(response.data);
  },

  getFilterOptions: async (): Promise<FilterOptions> => {
    const response = await api.get("/filter_options");
    return FilterOptionsSchema.parse(response.data);
  },

  search: async (
    query: string | null,
    category: string,
    filterOptions: Filter,
    page = 1,
    limit = 10,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post(
      "/search",
      { ...filterOptions, category },
      {
        params: { query, page, limit },
      },
    );
    return ScoredSearchResponseSchema.parse(response.data);
  },

  semanticSearch: async (
    query: string,
    category: string,
    filterOptions: Filter,
    page = 1,
    limit = 10,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post(
      "/semantic_search",
      { ...filterOptions, category },
      {
        params: { query, page, limit },
      },
    );
    return ScoredSearchResponseSchema.parse(response.data);
  },
};

export default api;
