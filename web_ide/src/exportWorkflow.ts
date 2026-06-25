import type { Edge } from "@xyflow/react";
import type { WorkflowNode } from "./nodes/nodes";
import type { FunctionNodeType } from "./nodes/FunctionNode";
import type { InputNodeType } from "./nodes/InputNode";
import type { OutputNodeType } from "./nodes/OutputNode";
import type {
  PythonWorkflowDefinitionWorkflow,
  PythonWorkflowDefinitionNode,
  PythonWorkflowDefinitionEdge,
} from "./interfaces/PythonWorkflowDefinitionSchema";

function tryParseValue(raw: string): unknown {
  if (raw === "") return undefined;
  try {
    return JSON.parse(raw) as unknown;
  } catch {
    return raw;
  }
}

export function toWorkflowDefinition(
  nodes: WorkflowNode[],
  edges: Edge[],
): PythonWorkflowDefinitionWorkflow {
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

  const pwdEdges: PythonWorkflowDefinitionEdge[] = edges
    .map((e): PythonWorkflowDefinitionEdge | null => {
      if (!nodeIds.has(e.source) || !nodeIds.has(e.target)) return null;
      return {
        source: e.source,
        source_handle: e.sourceHandle ?? null,
        target: e.target,
        target_handle: e.targetHandle ?? null,
      };
    })
    .filter((e): e is PythonWorkflowDefinitionEdge => e !== null);

  return {
    nodes: pwdNodes,
    edges: pwdEdges,
  };
}
