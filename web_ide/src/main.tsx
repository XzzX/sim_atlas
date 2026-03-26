import { createRoot } from "react-dom/client";
import { MainLayout } from "./MainLayout";
import { useNodesState, useEdgesState, type Edge } from "@xyflow/react";
import { allNodeMetadata } from "./initialData";
import { convertWorkflow } from "./importWorkflow";
import { simAtlasAPI } from "./services/api";

const fetchInitialNodesAndEdges = async (): Promise<{
  nodes: WorkflowNodeType[];
  edges: Edge[];
}> => {
  const urlSearchString = window.location.search;

  const params = new URLSearchParams(urlSearchString);
  const wf_hash = params.get("wf_hash");
  if (!wf_hash) return { nodes: [], edges: [] };
  const source_code = await simAtlasAPI.getNode(wf_hash);
  console.log(source_code);
  const { nodes, edges } = convertWorkflow(
    source_code.source_code,
    allNodeMetadata,
  );
  return { nodes, edges };
};

const { nodes: initialNodes, edges: initialEdges } =
  await fetchInitialNodesAndEdges();

export const WebMainLayout = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  return (
    <MainLayout
      allNodeMetadata={allNodeMetadata}
      nodes={nodes}
      setNodes={setNodes}
      onNodesChange={onNodesChange}
      edges={edges}
      setEdges={setEdges}
      onEdgesChange={onEdgesChange}
    />
  );
};

const container = document.getElementById("root");
if (!container) {
  throw new Error("Failed to find the root element");
}
const root = createRoot(container);
root.render(<WebMainLayout />);
