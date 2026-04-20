import axios from "axios";
import {
  NodeMetadata,
  NodeMetadataSchema,
  ScoredSearchResponse,
  ScoredSearchResponseSchema,
  Filter,
  FilterOptions,
  FilterOptionsSchema,
} from "../types/index";

const API_BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const simAtlasAPI = {
  getNode: async (nodeHash: string): Promise<NodeMetadata> => {
    const response = await api.get(`/nodes/${nodeHash}`);
    return NodeMetadataSchema.parse(response.data);
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
