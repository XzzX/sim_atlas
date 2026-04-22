import { z } from "zod";

// Recursive JSON-compatible value type mirroring AllowableDefaults in the Python model
type AllowableDefaults =
  | string
  | number
  | boolean
  | null
  | { [key: string]: AllowableDefaults }
  | AllowableDefaults[];

const AllowableDefaultsSchema: z.ZodType<AllowableDefaults> = z.lazy(() =>
  z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.null(),
    z.record(AllowableDefaultsSchema),
    z.array(AllowableDefaultsSchema),
  ]),
);

export const InputNodeSchema = z.object({
  id: z.number().int(),
  type: z.literal("input"),
  name: z.string(),
  value: AllowableDefaultsSchema.optional(),
});

export const OutputNodeSchema = z.object({
  id: z.number().int(),
  type: z.literal("output"),
  name: z.string(),
});

export const FunctionNodeSchema = z.object({
  id: z.number().int(),
  type: z.literal("function"),
  // Must be in 'module.function' format: no leading/trailing dot, at least one dot
  value: z
    .string()
    .regex(
      /^[^.]+(\.[^.]+)+$/,
      "FunctionNode 'value' must be in 'module.function' format (e.g. 'my_module.my_func')",
    ),
});

export const NodeSchema = z.discriminatedUnion("type", [
  InputNodeSchema,
  OutputNodeSchema,
  FunctionNodeSchema,
]);

export const EdgeSchema = z.object({
  source: z.number().int(),
  sourcePort: z.string().nullable().optional(),
  target: z.number().int(),
  targetPort: z.string().nullable().optional(),
});

export const PythonWorkflowDefinitionWorkflowSchema = z.object({
  version: z.string(),
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
export type PythonWorkflowDefinitionNode = z.infer<typeof NodeSchema>;
export type PythonWorkflowDefinitionEdge = z.infer<typeof EdgeSchema>;
export type PythonWorkflowDefinitionWorkflow = z.infer<
  typeof PythonWorkflowDefinitionWorkflowSchema
>;
