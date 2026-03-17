import axios from "axios";
import {
  NodeMetadata,
  ScoredSearchResponse,
  Filter,
  FilterOptions,
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
    return response.data as NodeMetadata;
  },

  getFilterOptions: async (): Promise<FilterOptions> => {
    const response = await api.get("/filter_options");
    return response.data as FilterOptions;
  },

  search: async (
    query: string | null,
    category: string,
    filterOptions: Filter,
  ): Promise<ScoredSearchResponse[]> => {
    const response = await api.post(
      "/search",
      { ...filterOptions, category },
      {
        params: { query },
      },
    );
    return response.data as ScoredSearchResponse[];
  },
};

export default api;
