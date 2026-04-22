import axios from "axios";
import {
  NodeResponseSchema,
  ScoredSearchResponseSchema,
  FilterOptionsSchema,
  type NodeResponse,
  type ScoredSearchResponse,
  type Filter,
  type FilterOptions,
} from "../interfaces/BackendSchema";

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

  search: async (
    query: string | null,
    filterOptions: Filter | null,
  ): Promise<ScoredSearchResponse> => {
    const response = await api.post(
      "/search",
      { ...filterOptions },
      {
        params: { query },
      },
    );
    return ScoredSearchResponseSchema.parse(response.data);
  },
};

export default api;
