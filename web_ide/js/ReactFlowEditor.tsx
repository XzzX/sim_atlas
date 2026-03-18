import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  addEdge,
  Background,
  MiniMap,
  type OnConnect,
  type NodeTypes,
  Panel,
} from "@xyflow/react";
import { Dispatch, SetStateAction } from "react";

import type {
  OnNodesChange,
  OnEdgesChange,
  Node,
  Edge,
  ReactFlowInstance,
} from "@xyflow/react";
import {
  type FunctionNodeType,
  type NodeData,
  FunctionNode,
} from "./nodes/FunctionNode";
import { type InputDataElement } from "./nodes/InputNode";
import { type OutputDataElement } from "./nodes/OutputNode";
import type { NodeMetadata } from "./interfaces/NodeMetadata";
import { AddNodeDialog } from "./dialogs/AddNodeDialog";
import { Button } from "./components/ui/button";
import { ImportDialog } from "./dialogs/ImportDialog";
import { convertWorkflow } from "./importWorkflow";
import dagre from "@dagrejs/dagre";
import { type WorkflowNode, nodeTypes } from "./nodes/nodes";
import type { ConditionalExpressionDataElement } from "./nodes/ConditionalExpressionNode";

interface ReactFlowEditor {
  allNodeMetadata: NodeMetadata[];
  nodes: WorkflowNode[];
  setNodes: Dispatch<SetStateAction<WorkflowNode[]>>;
  onNodesChange: OnNodesChange;
  edges: Edge[];
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  onEdgesChange: OnEdgesChange;
}

export const ReactFlowEditor: React.FC<ReactFlowEditor> = ({
  allNodeMetadata,
  nodes,
  setNodes,
  onNodesChange,
  edges,
  setEdges,
  onEdgesChange,
}) => {
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);
  const [isAddNodeDialogOpen, setIsAddNodeDialogOpen] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);

  const layoutGraph = () => {
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

    setNodes(newNodes);
    setEdges(edges);

    rfInstance.fitView().catch(() => {
      /* empty */
    });
  };

  useEffect(() => {
    if (rfInstance) {
      layoutGraph();
    }
  }, [rfInstance]);

  const onConnect: OnConnect = useCallback(
    (params) => {
      setEdges((edgesSnapshot) => addEdge(params, edgesSnapshot));
    },
    [setEdges],
  );

  const onAddNode = (
    type:
      | "InputNode"
      | "OutputNode"
      | "ConditionalExpressionNode"
      | "FunctionNode",
    data:
      | InputDataElement
      | OutputDataElement
      | ConditionalExpressionDataElement
      | NodeData,
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
    const { nodes, edges } = convertWorkflow(text, allNodeMetadata);
    rfInstance?.setNodes(nodes);
    rfInstance?.setEdges(edges);
    // setNodes(nodes);
    // setEdges(edges);
    layoutGraph();
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
      <ReactFlow
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
          allNodeMetadata={allNodeMetadata}
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
