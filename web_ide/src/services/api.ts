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
  getNode: async (nodeId: string): Promise<NodeResponse> => {
    const response = await api.get(`/nodes/${nodeId}`);
    return NodeResponseSchema.parse(response.data);
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
};

export default api;
