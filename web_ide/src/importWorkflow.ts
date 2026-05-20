import type { WorkflowNode } from "./nodes/nodes";
import {
  type PythonWorkflowDefinitionNode,
  PythonWorkflowDefinitionWorkflowSchema,
  type PythonWorkflowDefinitionWorkflow,
} from "./interfaces/PythonWorkflowDefinitionSchema";
import type { Edge } from "@xyflow/react";
import { simAtlasAPI } from "./services/api";
import type { NodeType } from "./interfaces/BackendSchema";

async function convertToNode(
  n: PythonWorkflowDefinitionNode,
): Promise<WorkflowNode | null> {
  if (n.type === "function" || n.type === "pack" || n.type === "unpack") {
    const nodeTypeFilter: NodeType | undefined =
      n.type === "pack" ? "pack"
      : n.type === "unpack" ? "unpack"
      : undefined;
    const response = await simAtlasAPI.search(
      n.value,
      nodeTypeFilter !== undefined ? { type: [nodeTypeFilter] } : null,
    );
    const meta = response.results.data.find(
      (item) => item.node.python_import === n.value,
    )?.node;
    if (!meta) {
      console.warn(`No metadata found for node with python_import: ${n.value}`);
      return null;
    }
    return {
      id: n.id.toString(),
      data: {
        label: n.value ?? meta.python_import.split(".").pop() ?? "",
        metadata: meta,
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
        value: n.value != null ? JSON.stringify(n.value) : "",
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

export async function toNodesAndEdges(
  workflow: PythonWorkflowDefinitionWorkflow,
): Promise<{
  nodes: WorkflowNode[];
  edges: Edge[];
}> {
  const nodes = (
    await Promise.all(workflow.nodes.map((n) => convertToNode(n)))
  ).filter((n) => n !== null);

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

export async function convertWorkflow(
  text: string,
): Promise<{ nodes: WorkflowNode[]; edges: Edge[] }> {
  try {
    const pwd: PythonWorkflowDefinitionWorkflow =
      PythonWorkflowDefinitionWorkflowSchema.parse(JSON.parse(text));
    return toNodesAndEdges(pwd);
  } catch (error) {
    console.error("Failed to convert workflow:", error);
  }
  return { nodes: [], edges: [] };
}
