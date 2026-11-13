import type { Edge } from "@xyflow/react";
import type { WorkflowNode } from "./nodes/nodes";
import type { FunctionNodeType } from "./nodes/FunctionNode";
import type { InputNodeType } from "./nodes/InputNode";
import type { OutputNodeType } from "./nodes/OutputNode";
import type { ConstantNodeType } from "./nodes/ConstantNode";
import { exportedConstant } from "./nodes/constantValue";
import type {
  PythonWorkflowDefinitionWorkflow,
  PythonWorkflowDefinitionNode,
  PythonWorkflowDefinitionEdge,
} from "./interfaces/PythonWorkflowDefinitionSchema";

export function tryParseValue(raw: string): unknown {
  if (raw === "") return undefined;
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return raw;
  }
}

export interface WorkflowDefinitionExportResult {
  workflow: PythonWorkflowDefinitionWorkflow;
  /** A constant whose value could not be exported. */
  errors: string[];
  /** A constant was renamed. */
  warnings: string[];
}

export function toWorkflowDefinition(
  nodes: WorkflowNode[],
  edges: Edge[],
): WorkflowDefinitionExportResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  // Constants are exported as inputs (see below), so their names must not
  // clash with a real input's or each other's.
  const usedNames = new Set(
    nodes.filter((n) => n.type === "InputNode").map((n) => n.data.label),
  );
  const uniqueName = (label: string): string => {
    let name = label;
    for (let index = 1; usedNames.has(name); index += 1) {
      name = `${label}_${index.toString()}`;
    }
    usedNames.add(name);
    return name;
  };

  const pwdNodes: PythonWorkflowDefinitionNode[] = nodes
    .map((node): PythonWorkflowDefinitionNode | null => {
      if (node.type === "FunctionNode") {
        const fn = node as FunctionNodeType;
        return {
          id: node.id,
          type: "function",
          python_import: fn.data.metadata.python_import ?? "",
          atlas_node_id: fn.data.metadata.id,
        };
      }

      if (node.type === "InputNode") {
        const inp = node as InputNodeType;
        const parsed = tryParseValue(inp.data.value);
        return {
          id: node.id,
          type: "input",
          name: inp.data.label,
          ...(parsed !== undefined ? { default: parsed } : {}),
        };
      }

      // PWD has no constant node: a constant becomes an input whose default
      // is its value, the closest PWD can express.
      if (node.type === "ConstantNode") {
        const { label, value } = (node as ConstantNodeType).data;
        const name = uniqueName(label);
        if (name !== label) {
          warnings.push(`Constant "${label}" was exported as the input "${name}".`);
        }
        return {
          id: node.id,
          type: "input",
          name,
          default: exportedConstant(label, value, errors),
        };
      }

      if (node.type === "OutputNode") {
        const out = node as OutputNodeType;
        return {
          id: node.id,
          type: "output",
          name: out.data.label,
        };
      }

      return null;
    })
    .filter((n): n is PythonWorkflowDefinitionNode => n !== null);

  const nodeIds = new Set(pwdNodes.map((n) => n.id));
  // A constant's handle names no port of the input node it is exported as.
  const constantsExportedAsInputs = new Set(
    nodes.filter((n) => n.type === "ConstantNode").map((n) => n.id),
  );

  const pwdEdges: PythonWorkflowDefinitionEdge[] = edges
    .map((e): PythonWorkflowDefinitionEdge | null => {
      if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) return null;
      return {
        source: e.source,
        source_handle: constantsExportedAsInputs.has(e.source)
          ? null
          : (e.sourceHandle ?? null),
        target: e.target,
        target_handle: e.targetHandle ?? null,
      };
    })
    .filter((e): e is PythonWorkflowDefinitionEdge => e !== null);

  return {
    workflow: {
      nodes: pwdNodes,
      edges: pwdEdges,
    },
    errors,
    warnings,
  };
}
