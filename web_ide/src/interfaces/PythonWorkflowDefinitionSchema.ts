import { z } from "zod";

export const InputNodeSchema = z.object({
  id: z.string().min(1),
  type: z.literal("input"),
  name: z.string(),
  default: z.any().optional(),
});

export const OutputNodeSchema = z.object({
  id: z.string().min(1),
  type: z.literal("output"),
  name: z.string(),
});

export const FunctionNodeSchema = z.object({
  id: z.string().min(1),
  type: z.literal("function"),
  python_import: z.string(),
  atlas_node_id: z.string().nullable().optional(),
});

export const PackNodeSchema = z.object({
  id: z.string().min(1),
  type: z.literal("pack"),
  python_import: z.string(),
  atlas_node_id: z.string().nullable().optional(),
});

export const UnpackNodeSchema = z.object({
  id: z.string().min(1),
  type: z.literal("unpack"),
  python_import: z.string(),
  atlas_node_id: z.string().nullable().optional(),
});

export const NodeSchema = z.discriminatedUnion("type", [
  InputNodeSchema,
  OutputNodeSchema,
  FunctionNodeSchema,
  PackNodeSchema,
  UnpackNodeSchema,
]);

export const EdgeSchema = z.object({
  source: z.string().min(1),
  source_handle: z.string().nullable().optional(),
  target: z.string().min(1),
  target_handle: z.string().nullable().optional(),
});

export const PythonWorkflowDefinitionWorkflowSchema = z.object({
  nodes: z.array(NodeSchema),
  edges: z.array(EdgeSchema),
});

// Inferred TypeScript types
export type PythonWorkflowDefinitionInputNode = z.infer<typeof InputNodeSchema>;
export type PythonWorkflowDefinitionOutputNode = z.infer<
  typeof OutputNodeSchema
>;
export type PythonWorkflowDefinitionFunctionNode = z.infer<
  typeof FunctionNodeSchema
>;
export type PythonWorkflowDefinitionPackNode = z.infer<typeof PackNodeSchema>;
export type PythonWorkflowDefinitionUnpackNode = z.infer<typeof UnpackNodeSchema>;
export type PythonWorkflowDefinitionNode = z.infer<typeof NodeSchema>;
export type PythonWorkflowDefinitionEdge = z.infer<typeof EdgeSchema>;
export type PythonWorkflowDefinitionWorkflow = z.infer<
  typeof PythonWorkflowDefinitionWorkflowSchema
>;
