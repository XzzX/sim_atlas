import { http, HttpResponse } from "msw";
import {
  linearWorkflow,
  linearExecutions,
  filterOptions,
  searchResponse,
  suggestions,
} from "../fixtures/nodes";

export const handlers = [
  // ":id" matches one path segment, so this cannot shadow the node route below
  http.get("/api/v1/nodes/:id/execution_results", () => HttpResponse.json(linearExecutions)),
  http.get("/api/v1/nodes/:id", () => HttpResponse.json(linearWorkflow)),
  http.get("/api/v1/filter_options", () => HttpResponse.json(filterOptions)),
  http.post("/api/v1/search", () => HttpResponse.json(searchResponse)),
  http.post("/api/v1/suggest", () => HttpResponse.json(suggestions)),
];
