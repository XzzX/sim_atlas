import { z } from "zod";

export const NodeTypeSchema = z.enum(["function", "workflow"]);
export type NodeType = z.infer<typeof NodeTypeSchema>;
export const NodeType = NodeTypeSchema.enum;

export const AnnotationSchema = z.object({
  has_default_value: z.boolean().optional(),
  label: z.string().nullish(),
  datatype: z.string().nullish(),
  unit: z.string().nullish(),
  quantity: z.string().nullish(),
  description: z.string().nullish(),
});
export type Annotation = z.infer<typeof AnnotationSchema>;

export const ReferenceSchema = z.object({
  label: z.string(),
  id: z.string(),
});
export type Reference = z.infer<typeof ReferenceSchema>;

export const FunctionRequestSchema = z.object({
  artifact_type: z.literal("function").optional(),
  name: z.string(),
  category: z.string(),
  keywords: z.array(z.string()),
  author_name: z.string(),
  author_email: z.string(),
  homepage_url: z.string(),
  documentation_url: z.string(),
  source_url: z.string(),
  python_import: z.string(),
  dependencies: z.array(z.string()).nullish(),
  source_code: z.string(),
  docstring: z.string(),
  brief_description: z.string().nullish(),
  description: z.string().nullish(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
  see_also: z.array(ReferenceSchema).optional(),
});
export type FunctionRequest = z.infer<typeof FunctionRequestSchema>;

// backward-compat alias
export const NodeRequestSchema = FunctionRequestSchema;
export type NodeRequest = FunctionRequest;

export const FunctionResponseSchema = z.object({
  artifact_type: z.literal("function"),
  id: z.string(),
  name: z.string(),
  category: z.string(),
  keywords: z.array(z.string()),
  author_name: z.string(),
  author_email: z.string(),
  creator_name: z.string(),
  creator_email: z.string(),
  creation_timestamp: z.string(),
  homepage_url: z.string().nullish(),
  documentation_url: z.string().nullish(),
  source_url: z.string().nullish(),
  python_import: z.string(),
  dependencies: z.array(z.string()).nullish(),
  source_code: z.string(),
  docstring: z.string(),
  brief_description: z.string().nullish(),
  description: z.string().nullish(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
  see_also: z.array(ReferenceSchema).optional(),
  used_by: z.array(ReferenceSchema).nullish(),
});
export type FunctionResponse = z.infer<typeof FunctionResponseSchema>;

// backward-compat alias
export const NodeResponseSchema = FunctionResponseSchema;
export type NodeResponse = FunctionResponse;

export const FunctionMetadataSchema = FunctionResponseSchema.extend({
  embedding: z.array(z.number()).nullish(),
  hash: z.string().optional(),
});
export type FunctionMetadata = z.infer<typeof FunctionMetadataSchema>;

// backward-compat alias
export const NodeMetadataSchema = FunctionMetadataSchema;
export type NodeMetadata = FunctionMetadata;

// --- Workflow graph node schemas ---

export const WfInputNodeSchema = z.object({
  type: z.literal("input"),
  node_id: z.string(),
  outputs: z.array(AnnotationSchema),
});
export type WfInputNode = z.infer<typeof WfInputNodeSchema>;

export const WfOutputNodeSchema = z.object({
  type: z.literal("output"),
  node_id: z.string(),
  inputs: z.array(AnnotationSchema),
});
export type WfOutputNode = z.infer<typeof WfOutputNodeSchema>;

export const WfFunctionNodeSchema = z.object({
  type: z.literal("function"),
  node_id: z.string(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
  atlas_id: z.string().nullish(),
});
export type WfFunctionNode = z.infer<typeof WfFunctionNodeSchema>;

export const WfNodeSchema = z.discriminatedUnion("type", [
  WfInputNodeSchema,
  WfOutputNodeSchema,
  WfFunctionNodeSchema,
]);
export type WfNode = z.infer<typeof WfNodeSchema>;

export const WfEdgeSchema = z.object({
  source_node: z.string(),
  source_port: z.string().nullish(),
  target_node: z.string(),
  target_port: z.string().nullish(),
});
export type WfEdge = z.infer<typeof WfEdgeSchema>;

export const WfDefinitionSchema = z.object({
  nodes: z.array(WfNodeSchema),
  edges: z.array(WfEdgeSchema),
});
export type WfDefinition = z.infer<typeof WfDefinitionSchema>;

// --- Workflow artifact schemas ---

export const WorkflowRequestSchema = z.object({
  artifact_type: z.literal("workflow").optional(),
  name: z.string(),
  category: z.string(),
  keywords: z.array(z.string()),
  author_name: z.string(),
  author_email: z.string(),
  homepage_url: z.string().nullish(),
  documentation_url: z.string().nullish(),
  source_url: z.string().nullish(),
  python_import: z.string().nullish(),
  dependencies: z.array(z.string()).nullish(),
  source_code: z.string(),
  docstring: z.string().nullish(),
  brief_description: z.string().nullish(),
  description: z.string().nullish(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
  see_also: z.array(ReferenceSchema).optional(),
  children: z.array(ReferenceSchema).optional(),
  wf_definition: WfDefinitionSchema.optional(),
});
export type WorkflowRequest = z.infer<typeof WorkflowRequestSchema>;

export const WorkflowResponseSchema = z.object({
  artifact_type: z.literal("workflow"),
  id: z.string(),
  name: z.string(),
  category: z.string(),
  keywords: z.array(z.string()),
  author_name: z.string(),
  author_email: z.string(),
  creator_name: z.string(),
  creator_email: z.string(),
  creation_timestamp: z.string(),
  homepage_url: z.string().nullish(),
  documentation_url: z.string().nullish(),
  source_url: z.string().nullish(),
  python_import: z.string().nullish(),
  dependencies: z.array(z.string()).nullish(),
  source_code: z.string(),
  docstring: z.string().nullish(),
  brief_description: z.string().nullish(),
  description: z.string().nullish(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
  see_also: z.array(ReferenceSchema).optional(),
  children: z.array(ReferenceSchema).optional(),
  wf_definition: WfDefinitionSchema.optional(),
});
export type WorkflowResponse = z.infer<typeof WorkflowResponseSchema>;

export const WorkflowMetadataSchema = WorkflowResponseSchema.extend({
  embedding: z.array(z.number()).nullish(),
  hash: z.string().optional(),
});
export type WorkflowMetadata = z.infer<typeof WorkflowMetadataSchema>;

export const ArtifactResponseSchema = z.discriminatedUnion("artifact_type", [
  FunctionResponseSchema,
  WorkflowResponseSchema,
]);
export type ArtifactResponse = z.infer<typeof ArtifactResponseSchema>;

export const ScoredSearchItemSchema = z.object({
  score: z.number(),
  node: z.discriminatedUnion("artifact_type", [
    FunctionResponseSchema,
    WorkflowResponseSchema,
  ]),
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

export const FilterSchema = z.object({
  category: z.string().nullish(),
  artifact_type: z.array(z.string()).nullish(),
  author: z.array(z.string()).nullish(),
  keywords: z.array(z.string()).nullish(),
  datatypes: z.array(z.string()).nullish(),
  units: z.array(z.string()).nullish(),
  quantities: z.array(z.string()).nullish(),
  port_type: z.enum(["inputs", "outputs", "both"]).nullable().optional(),
});
export type Filter = z.infer<typeof FilterSchema>;

export const FilterOptionsSchema = z.object({
  category: z.record(z.string(), z.array(z.string())),
  artifact_type: z.array(NodeTypeSchema),
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
  node_kind: z.enum(["function", "input", "output"]),
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
  history: z
    .array(
      z.object({ role: z.enum(["user", "assistant"]), content: z.string() }),
    )
    .optional(),
  session_id: z.string().optional(),
  user_id: z.string().optional(),
});
export type AgentRequest = z.infer<typeof AgentRequestSchema>;

export const AgentResponseSchema = z.object({
  nodes: z.array(GraphNodeContextSchema),
  edges: z.array(GraphEdgeContextSchema),
  message: z.string(),
});
export type AgentResponse = z.infer<typeof AgentResponseSchema>;

export const AgentSSEEventSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("reasoning"), content: z.string() }),
  z.object({
    type: z.literal("tool_call"),
    name: z.string(),
    args: z.record(z.string(), z.unknown()),
  }),
  z.object({
    type: z.literal("tool_result"),
    name: z.string(),
    content: z.string(),
  }),
  z.object({ type: z.literal("message"), content: z.string() }),
  z.object({
    type: z.literal("clarification"),
    question: z.string(),
    options: z.array(z.string()),
  }),
  z.object({
    type: z.literal("graph_update"),
    nodes: z.array(GraphNodeContextSchema),
    edges: z.array(GraphEdgeContextSchema),
  }),
  z.object({ type: z.literal("error"), message: z.string() }),
  z.object({ type: z.literal("validation"), errors: z.array(z.string()) }),
  z.object({ type: z.literal("truncated") }),
]);
export type AgentSSEEvent = z.infer<typeof AgentSSEEventSchema>;
