import { http, HttpResponse } from "msw";
import { linearWorkflow, linearExecutions, filterOptions, searchResponse } from "../fixtures/artifacts";

export const handlers = [
  // ":id" matches one path segment, so this cannot shadow the artifact route below
  http.get("/api/v1/artifacts/:id/execution_results", () => HttpResponse.json(linearExecutions)),
  http.get("/api/v1/artifacts/:id", () => HttpResponse.json(linearWorkflow)),
  http.get("/api/v1/filter_options", () => HttpResponse.json(filterOptions)),
  http.post("/api/v1/search", () => HttpResponse.json(searchResponse)),
];
