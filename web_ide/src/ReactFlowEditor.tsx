import { useCallback, useEffect, useRef, useState } from "react";
import {
  ReactFlow,
  addEdge,
  Background,
  MiniMap,
  type OnConnect,
  Panel,
} from "@xyflow/react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import type {
  OnNodesChange,
  OnEdgesChange,
  Edge,
  ReactFlowInstance,
} from "@xyflow/react";
import { type NodeData } from "./nodes/FunctionNode";
import { type InputDataElement } from "./nodes/InputNode";
import { type OutputDataElement } from "./nodes/OutputNode";
import { AddNodeDialog } from "./dialogs/AddNodeDialog";
import { Button } from "./components/ui/button";
import { ImportDialog } from "./dialogs/ImportDialog";
import { convertWorkflow } from "./importWorkflow";
import dagre from "@dagrejs/dagre";
import { type WorkflowNode, nodeTypes } from "./nodes/nodes";

interface ReactFlowEditor {
  nodes: WorkflowNode[];
  setNodes: Dispatch<SetStateAction<WorkflowNode[]>>;
  onNodesChange: OnNodesChange<WorkflowNode>;
  edges: Edge[];
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  onEdgesChange: OnEdgesChange;
  layoutRef?: MutableRefObject<() => void>;
}

export const ReactFlowEditor = ({
  nodes,
  setNodes,
  onNodesChange,
  edges,
  setEdges,
  onEdgesChange,
  layoutRef,
}: ReactFlowEditor) => {
  const _layoutRef = useRef<(() => void) | null>(null);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance<
    WorkflowNode,
    Edge
  > | null>(null);
  const [isAddNodeDialogOpen, setIsAddNodeDialogOpen] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);

  const layoutGraph = useCallback(() => {
    if (!rfInstance) return;
    const nodes = rfInstance.getNodes();
    const edges = rfInstance.getEdges();

    const dagreGraph = new dagre.graphlib.Graph();

    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: "LR" });

    nodes.forEach((node) => {
      dagreGraph.setNode(node.id, rfInstance.getNodesBounds([node]));
    });

    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const newNodes = nodes.map((node) => {
      const { width, height } = rfInstance.getNodesBounds([node]);
      const nodeWithPosition = dagreGraph.node(node.id);
      const newNode = {
        ...node,
        // We are shifting the dagre node position (anchor=center center) to the top left
        // so it matches the React Flow node anchor point (top left).
        position: {
          x: nodeWithPosition.x - width / 2,
          y: nodeWithPosition.y - height / 2,
        },
      };

      return newNode;
    });

    rfInstance.setNodes(newNodes);
    rfInstance.setEdges(edges);

    rfInstance.fitView().catch(() => {
      /* empty */
    });
  }, [rfInstance]);

  useEffect(() => {
    _layoutRef.current = layoutGraph;
    if (layoutRef) layoutRef.current = layoutGraph;
  }, [layoutGraph, layoutRef]);
  useEffect(() => {
    if (rfInstance) {
      layoutGraph();
    }
  }, [rfInstance, layoutGraph]);

  const onConnect: OnConnect = useCallback(
    (params) => {
      setEdges((edgesSnapshot) => addEdge(params, edgesSnapshot));
    },
    [setEdges],
  );

  const onAddNode = (
    type: "InputNode" | "OutputNode" | "FunctionNode",
    data: InputDataElement | OutputDataElement | NodeData,
  ) => {
    if (!rfInstance) {
      return;
    }
    if (contextMenuPos) {
      const newId = String(
        Math.max(...nodes.map((n) => parseInt(n.id) || 0), 0) + 1,
      );
      const newNode: WorkflowNode = {
        id: newId,
        data: data,
        position: { x: contextMenuPos.x, y: contextMenuPos.y },
        type: type,
      };
      setNodes([...nodes, newNode]);
      setContextMenuPos(null);
    }
  };

  const onImport = (text: string) => {
    void convertWorkflow(text).then(({ nodes, edges }) => {
      setNodes(nodes);
      setEdges(edges);
    });
  };

  const onExport = useCallback(() => {
    if (rfInstance) {
      const flow = rfInstance.toObject();
      console.log(JSON.stringify(flow));
    }
  }, [rfInstance]);

  const onPaneContextMenu = useCallback(
    (event: MouseEvent | React.MouseEvent) => {
      // Prevent default context menu
      event.preventDefault();

      // Check if click is on empty space (not on a node or edge)
      if (event.target === event.currentTarget) {
        if (rfInstance) {
          setContextMenuPos(
            rfInstance.screenToFlowPosition({
              x: event.clientX,
              y: event.clientY,
            }),
          );
          setIsAddNodeDialogOpen(true);
        }
      }
    },
    [rfInstance],
  );

  return (
    <div className="w-full h-screen">
      <ReactFlow<WorkflowNode, Edge>
        nodeTypes={nodeTypes}
        nodes={nodes}
        onNodesChange={onNodesChange}
        edges={edges}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onPaneContextMenu={onPaneContextMenu}
        onInit={setRfInstance}
        defaultEdgeOptions={{
          markerEnd: {
            type: "arrowclosed",
            width: 20,
            height: 20,
          },
        }}
        fitView
      >
        <Background />
        <MiniMap />
        <Panel position="top-left">
          <Button
            className="outline"
            onClick={() => {
              layoutGraph();
            }}
          >
            layout
          </Button>
          <Button onClick={onExport}>export</Button>
          <Button
            onClick={() => {
              setIsImportDialogOpen(true);
            }}
          >
            import
          </Button>
        </Panel>
        <AddNodeDialog
          isOpen={isAddNodeDialogOpen}
          onClose={() => {
            setIsAddNodeDialogOpen(false);
          }}
          onAdd={onAddNode}
        />
        <ImportDialog
          isOpen={isImportDialogOpen}
          onClose={() => {
            setIsImportDialogOpen(false);
          }}
          onLoad={onImport}
        />
      </ReactFlow>
    </div>
  );
};
