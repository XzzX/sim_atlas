import * as React from "react";
import type { Dispatch, SetStateAction } from "react";
import { ReactFlowEditor } from "./ReactFlowEditor";
import type { OnNodesChange, OnEdgesChange, Edge } from "@xyflow/react";
import "./index.css";
import type { WorkflowNode } from "./nodes/nodes";

interface MainLayoutProps {
  nodes: WorkflowNode[];
  setNodes: Dispatch<SetStateAction<WorkflowNode[]>>;
  onNodesChange: OnNodesChange<WorkflowNode>;
  edges: Edge[];
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  onEdgesChange: OnEdgesChange;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  nodes,
  setNodes,
  onNodesChange,
  edges,
  setEdges,
  onEdgesChange,
}) => {
  return (
    <div
      className="simflow"
      style={{ height: "100vh", display: "flex", flexDirection: "column" }}
    >
      <ReactFlowEditor
        nodes={nodes}
        setNodes={setNodes}
        onNodesChange={onNodesChange}
        edges={edges}
        setEdges={setEdges}
        onEdgesChange={onEdgesChange}
      />
    </div>
  );
};
