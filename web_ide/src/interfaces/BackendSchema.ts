import { z } from "zod";

export const NodeTypeSchema = z.enum([
  "function",
  "python_workflow_definition",
  "pyiron_workflow_function",
  "pyiron_core_node",
]);
export type NodeType = z.infer<typeof NodeTypeSchema>;
export const NodeType = NodeTypeSchema.enum;

export const AnnotationSchema = z.object({
  has_default_value: z.boolean().optional(), // default False in Pydantic
  label: z.string().nullish(),
  datatype: z.string().nullish(),
  unit: z.string().nullish(),
  quantity: z.string().nullish(),
});
export type Annotation = z.infer<typeof AnnotationSchema>;

export const NodeRequestSchema = z.object({
  author_name: z.string(),
  author_email: z.string(),

  name: z.string(),
  node_type: NodeTypeSchema,
  category: z.string(),

  keywords: z.array(z.string()),

  homepage_url: z.string(),
  documentation_url: z.string(),
  source_url: z.string(),

  python_import: z.string(),
  dependencies: z.array(z.string()).nullish(),

  source_code: z.string(),

  docstring: z.string(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
});
export type NodeRequest = z.infer<typeof NodeRequestSchema>;

export const NodeResponseSchema = z.object({
  author_name: z.string(),
  author_email: z.string(),

  creator_name: z.string(),
  creator_email: z.string(),
  creation_timestamp: z.string(),

  id: z.string(),
  name: z.string(),
  node_type: NodeTypeSchema,
  category: z.string(),

  keywords: z.array(z.string()),

  homepage_url: z.string(),
  documentation_url: z.string(),
  source_url: z.string(),

  python_import: z.string(),
  dependencies: z.array(z.string()).nullish(),

  source_code: z.string(),

  docstring: z.string(),
  ai_docstring: z.string(),

  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
});
export type NodeResponse = z.infer<typeof NodeResponseSchema>;

export const ScoredSearchItemSchema = z.object({
  score: z.number(),
  node: NodeResponseSchema,
});
export type ScoredSearchItem = z.infer<typeof ScoredSearchItemSchema>;

export const SearchResultsSchema = z.object({
  data: z.array(ScoredSearchItemSchema),
  page: z.number(),
  limit: z.number(),
  total_items: z.number(),
  total_pages: z.number(),
});
export type SearchResults = z.infer<typeof SearchResultsSchema>;

export const ScoredSearchResponseSchema = z.object({
  results: SearchResultsSchema,
  aggregations: z
    .record(z.string(), z.record(z.string(), z.number()))
    .nullish(),
});
export type ScoredSearchResponse = z.infer<typeof ScoredSearchResponseSchema>;

export const NodeMetadataSchema = NodeResponseSchema.extend({
  embedding: z.array(z.number()).nullish(),
});
export type NodeMetadata = z.infer<typeof NodeMetadataSchema>;

export const FilterSchema = z.object({
  category: z.string().nullish(),
  type: z.array(z.string()).nullish(),
  author: z.array(z.string()).nullish(),
  keywords: z.array(z.string()).nullish(),
  datatypes: z.array(z.string()).nullish(),
  units: z.array(z.string()).nullish(),
  quantities: z.array(z.string()).nullish(),
});
export type Filter = z.infer<typeof FilterSchema>;

export const FilterOptionsSchema = z.object({
  category: z.record(z.string(), z.array(z.string())),
  type: z.array(NodeTypeSchema),
  author: z.array(z.string()),
  keywords: z.array(z.string()),
  datatypes: z.array(z.string()),
  units: z.array(z.string()),
  quantities: z.array(z.string()),
});
export type FilterOptions = z.infer<typeof FilterOptionsSchema>;

// --- Agent types ---

export const GraphNodeContextSchema = z.object({
  graph_id: z.string(),
  atlas_node_id: z.string().nullish(),
  name: z.string(),
  short_description: z.string().nullish(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
});
export type GraphNodeContext = z.infer<typeof GraphNodeContextSchema>;

export const GraphEdgeContextSchema = z.object({
  source_graph_id: z.string(),
  source_handle: z.string(),
  target_graph_id: z.string(),
  target_handle: z.string(),
});
export type GraphEdgeContext = z.infer<typeof GraphEdgeContextSchema>;

export const AgentRequestSchema = z.object({
  query: z.string(),
  nodes: z.array(GraphNodeContextSchema),
  edges: z.array(GraphEdgeContextSchema),
});
export type AgentRequest = z.infer<typeof AgentRequestSchema>;

export const AgentSSEEventSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("tool_call"),
    name: z.string(),
    args: z.record(z.string(), z.unknown()),
  }),
  z.object({
    type: z.literal("tool_result"),
    name: z.string(),
    summary: z.string(),
  }),
  z.object({ type: z.literal("thinking"), content: z.string() }),
  z.object({ type: z.literal("message"), content: z.string() }),
  z.object({
    type: z.literal("done"),
    nodes: z.array(GraphNodeContextSchema),
    edges: z.array(GraphEdgeContextSchema),
  }),
  z.object({ type: z.literal("error"), message: z.string() }),
]);
export type AgentSSEEvent = z.infer<typeof AgentSSEEventSchema>;
