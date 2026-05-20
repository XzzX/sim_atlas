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
      const id = parseInt(node.id, 10);

      if (node.type === "FunctionNode") {
        const fn = node as FunctionNodeType;
        const nt = fn.data.metadata.node_type;
        return {
          id,
          type:
            nt === "pack" ? "pack"
            : nt === "unpack" ? "unpack"
            : "function",
          value: fn.data.metadata.python_import,
        };
      }

      if (node.type === "InputNode") {
        const inp = node as InputNodeType;
        const parsed = tryParseValue(inp.data.value);
        return {
          id,
          type: "input",
          name: inp.data.label,
          ...(parsed !== undefined ? { value: parsed as never } : {}),
        };
      }

      if (node.type === "OutputNode") {
        const out = node as OutputNodeType;
        return {
          id,
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
      const source = parseInt(e.source, 10);
      const target = parseInt(e.target, 10);
      if (!nodeIds.has(source) || !nodeIds.has(target)) return null;
      return {
        source,
        sourcePort: e.sourceHandle ?? null,
        target,
        targetPort: e.targetHandle ?? null,
      };
    })
    .filter((e): e is PythonWorkflowDefinitionEdge => e !== null);

  return {
    version: "0.1",
    nodes: pwdNodes,
    edges: pwdEdges,
  };
}
