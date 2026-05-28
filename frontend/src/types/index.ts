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
});
export type Annotation = z.infer<typeof AnnotationSchema>;

export const FunctionRequestSchema = z.object({
  author_name: z.string(),
  author_email: z.string(),

  name: z.string(),
  artifact_type: ArtifactTypeSchema,
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

  homepage_url: z.string(),
  documentation_url: z.string(),
  source_url: z.string(),

  python_import: z.string(),
  dependencies: z.array(z.string()).nullish(),

  source_code: z.string(),

  docstring: z.string(),
  ai_summary: z.string(),
  ai_description: z.string(),

  inputs: z.array(AnnotationSchema),
  outputs: z.array(AnnotationSchema),
});
export type FunctionResponse = z.infer<typeof FunctionResponseSchema>;

export const ScoredSearchItemSchema = z.object({
  score: z.number(),
  node: FunctionResponseSchema,
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
  category: z.string(),
  artifact_type: z.array(z.string()),
  author: z.array(z.string()),
  keywords: z.array(z.string()),
  datatypes: z.array(z.string()),
  units: z.array(z.string()),
  quantities: z.array(z.string()),
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
