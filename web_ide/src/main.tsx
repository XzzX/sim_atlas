import { createRoot } from "react-dom/client";
import { MainLayout } from "./MainLayout";
import { useNodesState, useEdgesState, type Edge } from "@xyflow/react";
import { convertWfDefinition } from "./importWorkflow";
import { simAtlasAPI } from "./services/api";
import type { WorkflowNode } from "./nodes/nodes";
import { HighlightProvider } from "./highlight/HighlightContext";

const fetchInitialNodesAndEdges = async (): Promise<{
  nodes: WorkflowNode[];
  edges: Edge[];
}> => {
  const urlSearchString = window.location.search;

  const params = new URLSearchParams(urlSearchString);
  const wf_id = params.get("wf_id");
  if (!wf_id) return { nodes: [], edges: [] };
  const artifact = await simAtlasAPI.getArtifact(wf_id);
  if (artifact.artifact_type !== "workflow" || !artifact.wf_definition) {
    return { nodes: [], edges: [] };
  }
  const { nodes, edges } = await convertWfDefinition(artifact.wf_definition);
  return { nodes, edges };
};

const { nodes: initialNodes, edges: initialEdges } =
  await fetchInitialNodesAndEdges();

export const WebMainLayout = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  return (
    <HighlightProvider edges={edges}>
      <MainLayout
        nodes={nodes}
        setNodes={setNodes}
        onNodesChange={onNodesChange}
        edges={edges}
        setEdges={setEdges}
        onEdgesChange={onEdgesChange}
      />
    </HighlightProvider>
  );
};

const container = document.getElementById("root");
if (!container) {
  throw new Error("Failed to find the root element");
}
const root = createRoot(container);
root.render(<WebMainLayout />);
