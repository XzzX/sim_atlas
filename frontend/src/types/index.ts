import { z } from "zod";

// ---------------------------------------------------------------------------
// TypeNode discriminated union + DataType wrapper
// ---------------------------------------------------------------------------

const SimpleNodeSchema = z.object({
  kind: z.literal("simple"),
  name: z.string(),
});

const GenericNodeSchema: z.ZodType<GenericNode> = z.lazy(() =>
  z.object({
    kind: z.literal("generic"),
    name: z.string(),
    args: z.array(TypeNodeSchema),
  }),
);

const UnionNodeSchema: z.ZodType<UnionNode> = z.lazy(() =>
  z.object({
    kind: z.literal("union"),
    members: z.array(TypeNodeSchema),
  }),
);

export type SimpleNode = z.infer<typeof SimpleNodeSchema>;
export interface GenericNode {
  kind: "generic";
  name: string;
  args: TypeNode[];
}
export interface UnionNode {
  kind: "union";
  members: TypeNode[];
}
export type TypeNode = SimpleNode | GenericNode | UnionNode;

export const TypeNodeSchema: z.ZodType<TypeNode> = z.union([
  SimpleNodeSchema,
  GenericNodeSchema,
  UnionNodeSchema,
]);

export const DataTypeSchema = z.object({
  ast: TypeNodeSchema,
  string: z.string(),
});
export type DataType = z.infer<typeof DataTypeSchema>;

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
  datatype: DataTypeSchema.nullish(),
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
  ai_summary: z.string(),
  ai_description: z.string(),

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
  category: z.string(),
  type: z.array(z.string()),
  author: z.array(z.string()),
  keywords: z.array(z.string()),
  datatypes: z.array(DataTypeSchema),
  units: z.array(z.string()),
  quantities: z.array(z.string()),
  port_type: z.enum(["inputs", "outputs", "both"]).nullable().optional(),
});
export type Filter = z.infer<typeof FilterSchema>;

export const FilterOptionsSchema = z.object({
  category: z.record(z.string(), z.array(z.string())),
  type: z.array(NodeTypeSchema),
  author: z.array(z.string()),
  keywords: z.array(z.string()),
  datatypes: z.array(DataTypeSchema),
  units: z.array(z.string()),
  quantities: z.array(z.string()),
});
export type FilterOptions = z.infer<typeof FilterOptionsSchema>;
