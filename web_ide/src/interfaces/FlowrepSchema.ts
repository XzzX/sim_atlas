/**
 * TypeScript mirror of flowrep's prospective recipe models (flowrep >= 0.6.2).
 *
 * Only the subset the IDE can express is modelled: a flat `workflow` recipe
 * whose children are all `atomic`. The flow-control recipes (`for_each`,
 * `while`, `if`, `try`) and `constant` have no counterpart on the canvas.
 *
 * Hand-written types rather than zod schemas: this format is write-only here,
 * and flowrep's real constraints — every child input sourced, acyclic edges,
 * output-edge keys equal to the output list — are cross-field rules that an
 * object schema cannot express anyway; `exportFlowrep.ts` checks them directly.
 */

/**
 * `pyiron_snippets.versions.VersionInfo` — a dataclass without defaults, so all
 * three keys must be present. `qualname: null` means the reference is a module.
 */
export interface FlowrepVersionInfo {
  module: string;
  qualname: string | null;
  version: string | null;
}

export type FlowrepRestrictedParamKind = "POSITIONAL_ONLY" | "KEYWORD_ONLY";

export interface FlowrepPythonReference {
  info: FlowrepVersionInfo;
  /** Inputs that may be left unconnected because Python supplies a default. */
  inputs_with_defaults: string[];
  restricted_input_kinds: Record<string, FlowrepRestrictedParamKind>;
}

export interface FlowrepAtomicRecipe {
  type: "atomic";
  inputs: string[];
  outputs: string[];
  description: string | null;
  reference: FlowrepPythonReference;
}

/**
 * Handles serialize to dotted `"node.port"` strings, and every edge map is
 * keyed by its *target* — that is how flowrep enforces a single source per
 * input port. A bare (dotless) name refers to a port of the workflow itself.
 */
export interface FlowrepWorkflowRecipe {
  type: "workflow";
  inputs: string[];
  outputs: string[];
  description: string | null;
  nodes: Record<string, FlowrepAtomicRecipe>;
  /** `"child.port"` -> `"workflowInput"` */
  input_edges: Record<string, string>;
  /** `"child.port"` -> `"child.port"` */
  edges: Record<string, string>;
  /** `"workflowOutput"` -> `"child.port"`, or `"workflowInput"` to pass through */
  output_edges: Record<string, string>;
  /** `null` for a graph authored in the IDE: it has no Python counterpart. */
  reference: FlowrepPythonReference | null;
}
