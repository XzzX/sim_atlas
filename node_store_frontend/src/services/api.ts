import axios from "axios";
import {
  NodeMetadata,
  ScoredSearchResponse,
  NodeType,
  FilterOptions,
} from "../types/index";

const API_BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const nodeAPI = {
  getNode: async (nodeHash: string): Promise<NodeMetadata> => {
    const response = await api.get(`/nodes/${nodeHash}`);
    return response.data;
  },

  search: async (
    query: string | null,
    filterOptions: FilterOptions,
  ): Promise<ScoredSearchResponse[]> => {
    const response = await api.post("/search", filterOptions, {
      params: { query },
    });
    return response.data;
  },
};

export default api;
