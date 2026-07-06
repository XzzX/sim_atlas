import { z } from "zod";

export const ArtifactTypeSchema = z.enum(["function", "workflow"]);
export type ArtifactType = z.infer<typeof ArtifactTypeSchema>;
export const ArtifactType = ArtifactTypeSchema.enum;

export const AnnotationSchema = z.object({
  has_default_value: z.boolean().optional(), // default False in Pydantic
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
  author_name: z.string(),
  author_email: z.string(),

  name: z.string(),
  artifact_type: ArtifactTypeSchema,
  category: z.string(),

  keywords: z.array(z.string()),

  homepage_url: z.string().nullish(),
  documentation_url: z.string().nullish(),
  source_url: z.string().nullish(),

  python_import: z.string(),
  dependencies: z.array(z.string()).nullish(),

  source_code: z.string(),

  docstring: z.string(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),

  brief_description: z.string().nullish(),
  description: z.string().nullish(),
  see_also: z.array(ReferenceSchema).optional().default([]),
});
export type FunctionRequest = z.infer<typeof FunctionRequestSchema>;

export const FunctionResponseSchema = z.object({
  author_name: z.string(),
  author_email: z.string(),

  creator_name: z.string(),
  creator_email: z.string(),
  creation_timestamp: z.string(),

  id: z.string(),
  name: z.string(),
  artifact_type: ArtifactTypeSchema,
  category: z.string(),

  keywords: z.array(z.string()),

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

  see_also: z.array(ReferenceSchema).optional().default([]),
  used_by: z.array(ReferenceSchema).nullish(),
});
export type FunctionResponse = z.infer<typeof FunctionResponseSchema>;

// --- Workflow schemas ---

const WfInputNodeSchema = z.object({
  type: z.literal("input"),
  node_id: z.string(),
  outputs: z.array(AnnotationSchema),
});

const WfOutputNodeSchema = z.object({
  type: z.literal("output"),
  node_id: z.string(),
  inputs: z.array(AnnotationSchema),
});

const WfFunctionNodeSchema = z.object({
  type: z.literal("function"),
  node_id: z.string(),
  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
  atlas_id: z.string().nullable(),
});

const WfNodeSchema = z.discriminatedUnion("type", [
  WfInputNodeSchema,
  WfOutputNodeSchema,
  WfFunctionNodeSchema,
]);

const WfEdgeSchema = z.object({
  source_node: z.string(),
  source_port: z.string().nullable().optional(),
  target_node: z.string(),
  target_port: z.string().nullable().optional(),
});

export const WorkflowDefinitionSchema = z.object({
  nodes: z.array(WfNodeSchema),
  edges: z.array(WfEdgeSchema),
});
export type WorkflowDefinition = z.infer<typeof WorkflowDefinitionSchema>;

export const WorkflowResponseSchema = z.object({
  author_name: z.string(),
  author_email: z.string(),

  creator_name: z.string(),
  creator_email: z.string(),
  creation_timestamp: z.string(),

  id: z.string(),
  name: z.string(),
  artifact_type: z.literal("workflow"),
  category: z.string(),
  keywords: z.array(z.string()),

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

  see_also: z.array(ReferenceSchema).optional().default([]),
  children: z.array(ReferenceSchema).optional().default([]),

  wf_definition: WorkflowDefinitionSchema,
});
export type WorkflowResponse = z.infer<typeof WorkflowResponseSchema>;

export const ArtifactResponseSchema = z.discriminatedUnion("artifact_type", [
  FunctionResponseSchema.extend({ artifact_type: z.literal("function") }),
  WorkflowResponseSchema,
]);
export type ArtifactResponse = z.infer<typeof ArtifactResponseSchema>;

export const ScoredSearchItemSchema = z.object({
  score: z.number(),
  node: ArtifactResponseSchema,
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

export const FunctionMetadataSchema = FunctionResponseSchema.extend({
  embedding: z.array(z.number()).nullish(),
});
export type FunctionMetadata = z.infer<typeof FunctionMetadataSchema>;

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
  artifact_type: z.array(ArtifactTypeSchema),
  author: z.array(z.string()),
  keywords: z.array(z.string()),
  datatypes: z.array(z.string()),
  units: z.array(z.string()),
  quantities: z.array(z.string()),
});
export type FilterOptions = z.infer<typeof FilterOptionsSchema>;

export const IOValueSchema = z.object({
  label: z.string(),
  value: z.union([z.string(), z.number(), z.boolean()]),
});
export type IOValue = z.infer<typeof IOValueSchema>;

export const ExecutionResultMetadataSchema = z.object({
  id: z.string(),
  author_name: z.string(),
  author_email: z.string(),
  creator_name: z.string(),
  creator_email: z.string(),
  creation_timestamp: z.string(),
  artifact_id: z.string(),
  inputs: z.array(IOValueSchema),
  outputs: z.string(),
  hash: z.string(),
});
export type ExecutionResultMetadata = z.infer<typeof ExecutionResultMetadataSchema>;

export const ExecutionResultListSchema = z.array(ExecutionResultMetadataSchema);
