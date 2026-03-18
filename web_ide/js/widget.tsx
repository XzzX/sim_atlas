import * as React from "react";
import { createRender, useModelState, useModel } from "@anywidget/react";
import { MainLayout } from "./MainLayout";
import {
  type Node,
  type Edge,
  type OnNodesChange,
  type OnEdgesChange,
  applyNodeChanges,
  applyEdgeChanges,
} from "@xyflow/react";
import { useCallback } from "react";

const render = createRender(() => {
  const model = useModel();

  const [nodes, setNodes] = useModelState<Node[]>("nodes");
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => {
      setNodes((nds) => applyNodeChanges(changes, nds));
    },
    [setNodes],
  );

  const [edges, setEdges] = useModelState<Edge[]>("edges");
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => {
      setEdges((eds) => applyEdgeChanges(changes, eds));
    },
    [setEdges],
  );

  return (
    <div style={{ position: "relative", height: "400px", width: "100%" }}>
      <MainLayout
        nodes={nodes}
        setNodes={setNodes}
        onNodesChange={onNodesChange}
        edges={edges}
        setEdges={setEdges}
        onEdgesChange={onEdgesChange}
      />
    </div>
  );
});

export default { render };
