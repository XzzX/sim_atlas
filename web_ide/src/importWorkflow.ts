import type { NodeMetadata } from "./interfaces/NodeMetadata";
import type { WorkflowNode } from "./nodes/nodes";
import {
  type PythonWorkflowDefinitionNode,
  PythonWorkflowDefinitionWorkflowSchema,
  type PythonWorkflowDefinitionWorkflow,
} from "./interfaces/PythonWorkflowDefinitionSchema";
import type { Edge } from "@xyflow/react";

function convertToNode(
  n: PythonWorkflowDefinitionNode,
  allNodeMetadata: NodeMetadata[],
): WorkflowNode | null {
  if (n.type === "function") {
    const metadata = allNodeMetadata.find(
      (node) => node.python_import === n.value,
    );
    if (!metadata) {
      console.warn(`No metadata found for node with python_import: ${n.value}`);
      return null;
    }
    return {
      id: n.id.toString(),
      data: {
        label: n.value ?? metadata.python_import?.split(".").pop() ?? "",
        metadata: metadata,
      },
      position: { x: Math.random() * 400, y: Math.random() * 400 }, // Placeholder positions
      type: "FunctionNode",
    };
  }
  if (n.type === "input") {
    return {
      id: n.id.toString(),
      data: {
        label: n.name ?? "Input",
        value: n.value ?? "",
      },
      position: { x: Math.random() * 400, y: Math.random() * 400 }, // Placeholder positions
      type: "InputNode",
    };
  }
  if (n.type === "output") {
    return {
      id: n.id.toString(),
      data: {
        label: n.name ?? "Output",
      },
      position: { x: Math.random() * 400, y: Math.random() * 400 }, // Placeholder positions
      type: "OutputNode",
    };
  }
  return null;
}

export function toNodesAndEdges(
  workflow: PythonWorkflowDefinitionWorkflow,
  allNodeMetadata: NodeMetadata[],
): {
  nodes: WorkflowNode[];
  edges: Edge[];
} {
  const nodes = workflow.nodes
    .map((n) => convertToNode(n, allNodeMetadata))
    .filter((n) => n !== null);

  const filtered_edges = workflow.edges.filter(
    (e) =>
      nodes.find((n) => n.id === String(e.source)) !== undefined &&
      nodes.find((n) => n.id === String(e.target)) !== undefined,
  );
  const edges: Edge[] = filtered_edges.map((e) => ({
    id: `e${e.source}.${e.sourcePort ?? ""}-${e.target}.${e.targetPort ?? ""}`,
    source: e.source.toString(),
    target: e.target.toString(),
    sourceHandle: e.sourcePort ?? undefined,
    targetHandle: e.targetPort ?? undefined,
  }));

  console.log("Converted nodes and edges:", { nodes, edges });

  return { nodes, edges };
}

export function convertWorkflow(
  text: string,
  allNodeMetadata: NodeMetadata[],
): { nodes: WorkflowNode[]; edges: Edge[] } {
  try {
    const pwd: PythonWorkflowDefinitionWorkflow =
      PythonWorkflowDefinitionWorkflowSchema.parse(JSON.parse(text));
    return toNodesAndEdges(pwd, allNodeMetadata);
  } catch (error) {
    console.error("Failed to convert workflow:", error);
  }
  return { nodes: [], edges: [] };
}
