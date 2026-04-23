import * as React from "react";
import { useRef } from "react";
import type { Dispatch, SetStateAction } from "react";
import { ReactFlowEditor } from "./ReactFlowEditor";
import type { OnNodesChange, OnEdgesChange, Edge } from "@xyflow/react";
import "./index.css";
import type { NodeResponse } from "./interfaces/BackendSchema";
import type { WorkflowNode } from "./nodes/nodes";
import { AgentPanel } from "./components/AgentPanel";

interface MainLayoutProps {
  allNodeMetadata: NodeResponse[];
  nodes: WorkflowNode[];
  setNodes: Dispatch<SetStateAction<WorkflowNode[]>>;
  onNodesChange: OnNodesChange<WorkflowNode>;
  edges: Edge[];
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  onEdgesChange: OnEdgesChange;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  allNodeMetadata,
  nodes,
  setNodes,
  onNodesChange,
  edges,
  setEdges,
  onEdgesChange,
}) => {
  const layoutRef = useRef<() => void>(() => {
    /* filled by ReactFlowEditor */
  });

  return (
    <div
      className="simflow"
      style={{ height: "100vh", display: "flex", flexDirection: "column" }}
    >
      {/* Main Content + Sidebar Container */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Main Content */}
        <div
          style={{
            flex: 1,
            overflow: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <ReactFlowEditor
            allNodeMetadata={allNodeMetadata}
            nodes={nodes}
            setNodes={setNodes}
            onNodesChange={onNodesChange}
            edges={edges}
            setEdges={setEdges}
            onEdgesChange={onEdgesChange}
            layoutRef={layoutRef}
          />
        </div>

        {/* Agent Panel */}
        <div
          style={{
            width: "384px",
            flexShrink: 0,
            overflow: "hidden",
            display: "flex",
          }}
        >
          <AgentPanel
            nodes={nodes}
            edges={edges}
            setNodes={setNodes}
            setEdges={setEdges}
            allNodeMetadata={allNodeMetadata}
            layoutRef={layoutRef}
          />
        </div>
      </div>
    </div>
  );
};
