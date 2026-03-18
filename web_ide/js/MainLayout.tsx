import * as React from "react";
import { Dispatch, SetStateAction } from "react";
import { ReactFlowEditor } from "./ReactFlowEditor";
import type { OnNodesChange, OnEdgesChange, Node, Edge } from "@xyflow/react";
import "./main.css";
import type { FunctionNodeType } from "./nodes/FunctionNode";
import type { NodeMetadata } from "./interfaces/NodeMetadata";
import { allNodeMetadata } from "./initialData";

interface MainLayoutProps {
  allNodeMetadata: NodeMetadata[];
  nodes: FunctionNodeType[];
  setNodes: Dispatch<SetStateAction<FunctionNodeType[]>>;
  onNodesChange: OnNodesChange;
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
          />
        </div>

        {/* Static Right Sidebar */}
        {/* <div
          style={{
            width: "280px",
            backgroundColor: "#f8f9fa",
            borderLeft: "1px solid #dee2e6",
            overflow: "auto",
            padding: "20px",
          }}
        >
          <h5 className="mb-3">Sidebar Panel</h5>
          <div
            style={{ display: "flex", flexDirection: "column", gap: "20px" }}
          >
            <div>
              <h6>Settings</h6>
              <p style={{ fontSize: "0.875rem", color: "#6c757d", margin: 0 }}>
                Configure your application here
              </p>
            </div>
            <div>
              <h6>Options</h6>
              <p style={{ fontSize: "0.875rem", color: "#6c757d", margin: 0 }}>
                Additional options and tools
              </p>
            </div>
            <div>
              <h6>Information</h6>
              <p style={{ fontSize: "0.875rem", color: "#6c757d", margin: 0 }}>
                Help and information section
              </p>
            </div>
          </div>
        </div> */}
      </div>
    </div>
  );
};
