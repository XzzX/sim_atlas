import type { Edge } from "@xyflow/react";
import type { WorkflowNode } from "./nodes/nodes";
import type { FunctionNodeType } from "./nodes/FunctionNode";
import type { InputNodeType } from "./nodes/InputNode";
import type { OutputNodeType } from "./nodes/OutputNode";
import type { Annotation } from "./interfaces/BackendSchema";
import type {
  FlowrepAtomicRecipe,
  FlowrepVersionInfo,
  FlowrepWorkflowRecipe,
} from "./interfaces/FlowrepSchema";
import { tryParseValue } from "./exportWorkflow";

export interface FlowrepExportResult {
  recipe: FlowrepWorkflowRecipe;
  /** flowrep would reject this recipe. */
  errors: string[];
  /** flowrep accepts this recipe, but something was renamed or dropped. */
  warnings: string[];
}

/** Hard keywords only — `match`, `case`, `type` and `_` are legal identifiers. */
const PYTHON_KEYWORDS = new Set([
  "False",
  "None",
  "True",
  "and",
  "as",
  "assert",
  "async",
  "await",
  "break",
  "class",
  "continue",
  "def",
  "del",
  "elif",
  "else",
  "except",
  "finally",
  "for",
  "from",
  "global",
  "if",
  "import",
  "in",
  "is",
  "lambda",
  "nonlocal",
  "not",
  "or",
  "pass",
  "raise",
  "return",
  "try",
  "while",
  "with",
  "yield",
]);

/** flowrep reserves these because they name the two port groups. */
const RESERVED_LABELS = new Set(["inputs", "outputs"]);

/**
 * Coerce free text into a valid flowrep label (see flowrep/base_models.py),
 * or return null when nothing usable is left so the caller can substitute a
 * fallback. The ASCII-only character class is stricter than Python's
 * `str.isidentifier()`, which also accepts letters outside ASCII; mangling
 * those is preferable to emitting labels this exporter cannot round-trip.
 */
function toLabelBase(raw: string): string | null {
  let label = raw.trim().replace(/[^A-Za-z0-9_]+/g, "_");
  if (label === "") return null;
  if (/^[0-9]/.test(label)) label = `_${label}`;
  if (PYTHON_KEYWORDS.has(label) || RESERVED_LABELS.has(label)) label = `${label}_`;
  return label;
}

interface NameAllocator {
  allocate: (base: string) => string;
}

/**
 * Hands out unique labels. With `alwaysIndex` every name gets a numeric suffix,
 * which reproduces flowrep's node-label convention (`mul` -> `mul_0`, see
 * flowrep/parsers/label_helpers.py); without it a base name is used as-is until
 * it collides.
 */
function createNameAllocator(alwaysIndex: boolean): NameAllocator {
  const used = new Set<string>();
  const counters = new Map<string, number>();
  return {
    allocate(base: string): string {
      if (!alwaysIndex && !used.has(base)) {
        used.add(base);
        return base;
      }
      let index = counters.get(base) ?? 0;
      let candidate = `${base}_${index}`;
      while (used.has(candidate)) {
        index += 1;
        candidate = `${base}_${index}`;
      }
      counters.set(base, index + 1);
      used.add(candidate);
      return candidate;
    },
  };
}

interface PortNames {
  /** Emitted port names, positionally aligned with the annotations. */
  names: string[];
  /** React Flow handle id -> emitted port name. */
  byHandle: Map<string, string>;
}

function allocatePorts(
  annotations: Annotation[],
  nodeLabel: string,
  fallbackPrefix: string,
  warnings: string[],
): PortNames {
  const allocator = createNameAllocator(false);
  const names: string[] = [];
  const byHandle = new Map<string, string>();

  annotations.forEach((annotation, index) => {
    // Must match the handle id rendered by FunctionNode exactly, or edge
    // lookup silently misses.
    const handleId = annotation.label ?? String(index);
    const name = allocator.allocate(
      toLabelBase(annotation.label ?? "") ?? `${fallbackPrefix}_${index}`,
    );
    names.push(name);
    if (byHandle.has(handleId)) {
      warnings.push(
        `"${nodeLabel}" declares the port "${handleId}" more than once; only the first is wired.`,
      );
    } else {
      byHandle.set(handleId, name);
      if (name !== handleId) {
        warnings.push(`Port "${handleId}" of "${nodeLabel}" was renamed to "${name}".`);
      }
    }
  });

  return { names, byHandle };
}

/** Split a dotted import the way flowrep does: `rsplit(".", 1)`. */
function toVersionInfo(pythonImport: string): FlowrepVersionInfo {
  const separator = pythonImport.lastIndexOf(".");
  if (separator === -1) {
    return { module: pythonImport, qualname: null, version: null };
  }
  return {
    module: pythonImport.slice(0, separator),
    qualname: pythonImport.slice(separator + 1),
    version: null,
  };
}

interface ChildNode {
  label: string;
  recipe: FlowrepAtomicRecipe;
  inputPorts: Map<string, string>;
  outputPorts: Map<string, string>;
}

function toChildNode(
  node: FunctionNodeType,
  labels: NameAllocator,
  errors: string[],
  warnings: string[],
): ChildNode {
  const metadata = node.data.metadata;
  const pythonImport = metadata.python_import ?? "";
  const label = labels.allocate(
    toLabelBase(pythonImport.split(".").pop() ?? "") ??
      toLabelBase(node.data.label) ??
      "node",
  );

  if (pythonImport === "") {
    errors.push(
      `"${label}" has no python import path; flowrep needs one to reference the function. ` +
        `Exported as the bare module "${label}".`,
    );
  } else if (!pythonImport.includes(".")) {
    warnings.push(
      `"${pythonImport}" has no module part; exported as a module reference without a qualname.`,
    );
  }

  const inputs = allocatePorts(metadata.inputs, label, "arg", warnings);
  const outputs = allocatePorts(metadata.outputs, label, "output", warnings);
  const description = (metadata.brief_description ?? metadata.docstring ?? "").trim();

  return {
    label,
    inputPorts: inputs.byHandle,
    outputPorts: outputs.byHandle,
    recipe: {
      type: "atomic",
      inputs: inputs.names,
      outputs: outputs.names,
      description: description === "" ? null : description,
      reference: {
        info: toVersionInfo(pythonImport === "" ? label : pythonImport),
        inputs_with_defaults: metadata.inputs
          .map((annotation, index) =>
            annotation.has_default_value === true ? inputs.names[index] : null,
          )
          .filter((name): name is string => name !== null),
        restricted_input_kinds: {},
      },
    },
  };
}

/** Node labels involved in a cycle, via Kahn over `edges` (mirrors flowrep's check). */
function findCycleLabels(labels: string[], edges: Record<string, string>): string[] {
  const pending = new Map(labels.map((label) => [label, new Set<string>()]));
  for (const [target, source] of Object.entries(edges)) {
    pending.get(target.split(".", 1)[0])?.add(source.split(".", 1)[0]);
  }

  let settled = true;
  while (settled) {
    settled = false;
    for (const [label, dependencies] of pending) {
      if (dependencies.size > 0) continue;
      pending.delete(label);
      for (const remaining of pending.values()) remaining.delete(label);
      settled = true;
    }
  }
  return [...pending.keys()];
}

function isFunctionNode(node: WorkflowNode): node is FunctionNodeType {
  return node.type === "FunctionNode";
}

function isInputNode(node: WorkflowNode): node is InputNodeType {
  return node.type === "InputNode";
}

function isOutputNode(node: WorkflowNode): node is OutputNodeType {
  return node.type === "OutputNode";
}

/** A resolved edge endpoint: a child handle, or a port of the workflow itself. */
type Endpoint =
  | { kind: "child"; child: ChildNode; port: string }
  | { kind: "workflow"; name: string };

/**
 * Convert the canvas graph into a flowrep `WorkflowRecipe`.
 *
 * Input nodes become workflow inputs (their values are dropped — flowrep stores
 * only the *names* of defaulted parameters, never values) and output nodes
 * become workflow outputs; only function nodes become recipe nodes, all of them
 * `atomic`. The recipe is always returned, even when `errors` is non-empty, so
 * the caller can show what would be emitted alongside what is wrong with it.
 */
export function toFlowrepRecipe(
  nodes: WorkflowNode[],
  edges: Edge[],
): FlowrepExportResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  const nodeLabels = createNameAllocator(true);
  const inputLabels = createNameAllocator(false);
  const outputLabels = createNameAllocator(false);

  const children = new Map<string, ChildNode>();
  const workflowInputs = new Map<string, string>();
  const workflowOutputs = new Map<string, string>();

  for (const node of nodes) {
    if (isFunctionNode(node)) {
      children.set(node.id, toChildNode(node, nodeLabels, errors, warnings));
      continue;
    }
    if (isInputNode(node)) {
      const name = inputLabels.allocate(toLabelBase(node.data.label) ?? "input");
      if (name !== node.data.label) {
        warnings.push(`Input "${node.data.label}" was renamed to "${name}".`);
      }
      if (tryParseValue(node.data.value) !== undefined) {
        warnings.push(
          `The value of input "${name}" was dropped: flowrep workflow inputs carry no values.`,
        );
      }
      workflowInputs.set(node.id, name);
      continue;
    }
    if (isOutputNode(node)) {
      const name = outputLabels.allocate(toLabelBase(node.data.label) ?? "output");
      if (name !== node.data.label) {
        warnings.push(`Output "${node.data.label}" was renamed to "${name}".`);
      }
      workflowOutputs.set(node.id, name);
    }
  }

  /**
   * Resolve one end of an edge. Input and output nodes have a single hardcoded
   * handle that is absent from imported graphs, so their handle id is ignored;
   * a missing handle on a function node falls back to its only port.
   */
  const resolve = (
    nodeId: string,
    handle: string | null | undefined,
    side: "source" | "target",
  ): Endpoint | null => {
    const child = children.get(nodeId);
    if (child !== undefined) {
      const ports = side === "source" ? child.outputPorts : child.inputPorts;
      if (handle === null || handle === undefined) {
        const only = [...ports.values()];
        if (only.length === 1) return { kind: "child", child, port: only[0] };
        errors.push(
          `An edge ${side === "source" ? "from" : "to"} "${child.label}" names no port ` +
            `and the node has ${only.length.toString()} of them; the edge was dropped.`,
        );
        return null;
      }
      const port = ports.get(handle);
      if (port === undefined) {
        errors.push(
          `"${child.label}" has no ${side === "source" ? "output" : "input"} "${handle}" ` +
            `any more; the edge was dropped.`,
        );
        return null;
      }
      return { kind: "child", child, port };
    }

    const name =
      side === "source" ? workflowInputs.get(nodeId) : workflowOutputs.get(nodeId);
    if (name !== undefined) return { kind: "workflow", name };

    const reversed =
      side === "source" ? workflowOutputs.get(nodeId) : workflowInputs.get(nodeId);
    if (reversed !== undefined) {
      errors.push(
        `"${reversed}" is used as an edge ${side}, which flowrep cannot express; ` +
          `the edge was dropped.`,
      );
    }
    return null;
  };

  const handleOf = (endpoint: Endpoint): string =>
    endpoint.kind === "child"
      ? `${endpoint.child.label}.${endpoint.port}`
      : endpoint.name;

  const childSources = new Map<string, { source: string; fromWorkflowInput: boolean }>();
  const outputSources = new Map<string, string>();

  for (const edge of edges) {
    const source = resolve(edge.source, edge.sourceHandle, "source");
    const target = resolve(edge.target, edge.targetHandle, "target");
    if (source === null || target === null) continue;

    const sourceHandle = handleOf(source);
    const targetHandle = handleOf(target);
    const existing =
      target.kind === "child"
        ? childSources.get(targetHandle)?.source
        : outputSources.get(targetHandle);
    if (existing !== undefined) {
      if (existing !== sourceHandle) {
        errors.push(
          `"${targetHandle}" is fed by both "${existing}" and "${sourceHandle}"; flowrep ` +
            `allows exactly one source per port, so only "${existing}" was kept.`,
        );
      }
      continue;
    }

    if (target.kind === "child") {
      childSources.set(targetHandle, {
        source: sourceHandle,
        fromWorkflowInput: source.kind === "workflow",
      });
    } else {
      outputSources.set(targetHandle, sourceHandle);
    }
  }

  // Key order follows flowrep's own model_dump, so exports diff cleanly.
  const recipe: FlowrepWorkflowRecipe = {
    type: "workflow",
    inputs: [...workflowInputs.values()],
    outputs: [],
    description: null,
    nodes: {},
    input_edges: {},
    edges: {},
    output_edges: {},
    reference: null,
  };

  for (const child of children.values()) {
    recipe.nodes[child.label] = child.recipe;
  }

  // Emitted in declaration order rather than edge order, again for stable diffs.
  for (const child of children.values()) {
    const defaulted = new Set(child.recipe.reference.inputs_with_defaults);
    for (const port of child.recipe.inputs) {
      const target = `${child.label}.${port}`;
      const fed = childSources.get(target);
      if (fed === undefined) {
        if (!defaulted.has(port)) {
          errors.push(
            `"${target}" has no incoming edge and the function declares no default for it.`,
          );
        }
        continue;
      }
      const map = fed.fromWorkflowInput ? recipe.input_edges : recipe.edges;
      map[target] = fed.source;
    }
  }

  for (const name of workflowOutputs.values()) {
    const source = outputSources.get(name);
    if (source === undefined) {
      errors.push(
        `Output "${name}" has no incoming edge; flowrep requires exactly one source per ` +
          `workflow output, so the output was omitted from the recipe.`,
      );
      continue;
    }
    recipe.outputs.push(name);
    recipe.output_edges[name] = source;
  }

  const cycle = findCycleLabels(Object.keys(recipe.nodes), recipe.edges);
  if (cycle.length > 0) {
    errors.push(`The edges form a cycle through: ${cycle.join(", ")}.`);
  }

  return { recipe, errors, warnings };
}
