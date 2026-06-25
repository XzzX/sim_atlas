import type { WorkflowNode } from "./nodes/nodes";
import {
  type PythonWorkflowDefinitionNode,
  PythonWorkflowDefinitionWorkflowSchema,
  type PythonWorkflowDefinitionWorkflow,
} from "./interfaces/PythonWorkflowDefinitionSchema";
import type { Edge } from "@xyflow/react";
import { simAtlasAPI } from "./services/api";
import type { NodeType as ArtifactType } from "./interfaces/BackendSchema";

async function convertToNode(
  n: PythonWorkflowDefinitionNode,
): Promise<WorkflowNode | null> {
  if (n.type === "function" || n.type === "pack" || n.type === "unpack") {
    const nodeTypeFilter: ArtifactType | undefined = undefined;

    // Prefer direct lookup by atlas_node_id; fall back to keyword search
    let meta =
      n.atlas_node_id != null
        ? (await simAtlasAPI.getNode(n.atlas_node_id).catch(() => null))
        : null;

    if (!meta) {
      const response = await simAtlasAPI.search(
        n.python_import,
        nodeTypeFilter !== undefined ? { artifact_type: [nodeTypeFilter] } : null,
      );
      meta =
        response.results.data.find(
          (item) => item.node.python_import === n.python_import,
        )?.node ?? null;
    }

    if (!meta) {
      console.warn(`No metadata found for node with python_import: ${n.python_import}`);
      return null;
    }
    return {
      id: n.id,
      data: {
        label: n.python_import.split(".").pop() ?? n.python_import,
        metadata: meta,
      },
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      type: "FunctionNode",
    };
  }
  if (n.type === "input") {
    return {
      id: n.id,
      data: {
        label: n.name ?? "Input",
        value: n.default != null ? JSON.stringify(n.default) : "",
      },
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      type: "InputNode",
    };
  }
  if (n.type === "output") {
    return {
      id: n.id,
      data: {
        label: n.name ?? "Output",
      },
      position: { x: Math.random() * 400, y: Math.random() * 400 },
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

  const nodeIdSet = new Set(nodes.map((n) => n.id));
  const filtered_edges = workflow.edges.filter(
    (e) => nodeIdSet.has(e.source) && nodeIdSet.has(e.target),
  );
  const edges: Edge[] = filtered_edges.map((e) => ({
    id: `e${e.source}.${e.source_handle ?? ""}-${e.target}.${e.target_handle ?? ""}`,
    source: e.source,
    target: e.target,
    sourceHandle: e.source_handle ?? undefined,
    targetHandle: e.target_handle ?? undefined,
  }));

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
