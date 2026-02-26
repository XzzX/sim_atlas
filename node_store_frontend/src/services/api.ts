import axios from "axios";
import { NodeMetadata, ScoredSearchResponse, NodeType } from "../types/index";

const API_BASE_URL = "/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

export const nodeAPI = {
  /**
   * List all nodes with optional filtering
   */
  listNodes: async (
    qualname?: string,
    type?: NodeType,
  ): Promise<NodeMetadata[]> => {
    const response = await api.get("/nodes", {
      params: {
        ...(qualname && { qualname }),
        ...(type && { type }),
      },
    });
    return response.data;
  },

  /**
   * Get a specific node by hash
   */
  getNode: async (nodeHash: string): Promise<NodeMetadata> => {
    const response = await api.get(`/nodes/${nodeHash}`);
    return response.data;
  },

  /**
   * Search nodes by query string
   */
  search: async (query: string): Promise<ScoredSearchResponse[]> => {
    const response = await api.post("/search", null, {
      params: { query },
    });
    return response.data;
  },

  /**
   * Perform semantic search on nodes
   */
  semanticSearch: async (
    query: string,
    limit: number = 10,
  ): Promise<ScoredSearchResponse[]> => {
    const response = await api.post("/semantic_search", null, {
      params: { query, limit },
    });
    return response.data;
  },
};

export default api;
