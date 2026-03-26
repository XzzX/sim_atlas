import type { Edge } from "@xyflow/react";
import type { NodeMetadata, WorkflowNodeType } from "./interfaces/NodeMetadata";
import * as PWD from "./interfaces/PythonWorkflowDefinition";

export function convertWorkflow(
  text: string,
  allNodeMetadata: NodeMetadata[],
): { nodes: WorkflowNodeType[]; edges: Edge[] } {
  try {
    const pwd = PWD.Convert.toPythonWorkflowDefinition(text);
    return PWD.toNodesAndEdges(pwd, allNodeMetadata);
  } catch (error) {
    console.error("Failed to convert workflow:", error);
  }
  return { nodes: [], edges: [] };
}
