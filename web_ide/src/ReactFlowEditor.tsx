import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  addEdge,
  Background,
  MiniMap,
  type OnConnect,
  type FinalConnectionState,
  Panel,
} from "@xyflow/react";
import type { Dispatch, MutableRefObject, SetStateAction } from "react";

import type {
  OnNodesChange,
  OnEdgesChange,
  OnConnectStart,
  Edge,
  ReactFlowInstance,
} from "@xyflow/react";
import { type NodeData, type FunctionNodeType } from "./nodes/FunctionNode";
import { type Annotation, type Filter } from "./interfaces/BackendSchema";
import { type InputDataElement } from "./nodes/InputNode";
import { type OutputDataElement } from "./nodes/OutputNode";
import { AddNodeDialog } from "./dialogs/AddNodeDialog";
import { Button } from "./components/ui/button";
import { ImportDialog } from "./dialogs/ImportDialog";
import { convertWorkflow } from "./importWorkflow";
import dagre from "@dagrejs/dagre";
import { type WorkflowNode, nodeTypes } from "./nodes/nodes";
import { useHighlight } from "./highlight/useHighlight";

interface ReactFlowEditor {
  nodes: WorkflowNode[];
  setNodes: Dispatch<SetStateAction<WorkflowNode[]>>;
  onNodesChange: OnNodesChange<WorkflowNode>;
  edges: Edge[];
  setEdges: Dispatch<SetStateAction<Edge[]>>;
  onEdgesChange: OnEdgesChange;
  layoutRef?: MutableRefObject<() => void>;
}

interface PendingConnection {
  nodeId: string;
  handleId: string;
  handleType: "source" | "target";
  annotation: Annotation | null;
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
  const [pendingConnection, setPendingConnection] =
    useState<PendingConnection | null>(null);

  const { highlightState, setInteraction } = useHighlight();

  const layoutGraph = useCallback(() => {
    if (!rfInstance) return;
    const nodes = rfInstance.getNodes();
    const edges = rfInstance.getEdges();

    const dagreGraph = new dagre.graphlib.Graph();

    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: "LR" });

    nodes.forEach((node) => {
      const bounds = rfInstance.getNodesBounds([node]);
      dagreGraph.setNode(node.id, {
        width: bounds.width || 150,
        height: bounds.height || 60,
      });
    });

    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const newNodes = nodes.map((node) => {
      const bounds = rfInstance.getNodesBounds([node]);
      const width = bounds.width || 150;
      const height = bounds.height || 60;
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

  const onConnectStart: OnConnectStart = useCallback(
    (_event, params) => {
      const { nodeId, handleId, handleType } = params;
      if (!nodeId || !handleId || !handleType) return;
      const allNodes = rfInstance?.getNodes() ?? [];
      const srcNode = allNodes.find((n) => n.id === nodeId);
      let fromAnnotation: Annotation | null = null;
      if (srcNode?.type === "FunctionNode") {
        const fn = srcNode as FunctionNodeType;
        const ports =
          handleType === "source"
            ? fn.data.metadata.outputs
            : fn.data.metadata.inputs;
        const idx = ports.findIndex(
          (p, i) => (p.label ?? i.toString()) === handleId,
        );
        fromAnnotation = idx >= 0 ? (ports[idx] ?? null) : null;
      }
      setInteraction({
        mode: "dragging",
        fromNodeId: nodeId,
        fromHandleId: handleId,
        fromAnnotation,
      });
    },
    [rfInstance, setInteraction],
  );

  const onConnectEnd = useCallback(
    (event: MouseEvent | TouchEvent, connectionState: FinalConnectionState) => {
      const fromNode = connectionState.fromNode;
      const fromHandle = connectionState.fromHandle;
      if (!rfInstance || !fromNode || connectionState.toNode !== null) return;
      if (!fromHandle?.id || !fromHandle.type) return;

      const allNodes = rfInstance.getNodes();
      const srcNode = allNodes.find((n) => n.id === fromNode.id);
      let annotation: Annotation | null = null;
      if (srcNode?.type === "FunctionNode") {
        const fnNode = srcNode as FunctionNodeType;
        const ports =
          fromHandle.type === "source"
            ? fnNode.data.metadata.outputs
            : fnNode.data.metadata.inputs;
        const idx = ports.findIndex(
          (p, i) => (p.label ?? i.toString()) === fromHandle.id,
        );
        annotation = idx >= 0 ? (ports[idx] ?? null) : null;
      }

      const clientX = "clientX" in event ? event.clientX : 0;
      const clientY = "clientY" in event ? event.clientY : 0;
      const pos = rfInstance.screenToFlowPosition({ x: clientX, y: clientY });
      setPendingConnection({
        nodeId: fromNode.id,
        handleId: fromHandle.id,
        handleType: fromHandle.type,
        annotation,
      });
      setContextMenuPos(pos);
      setIsAddNodeDialogOpen(true);
      setInteraction({ mode: "idle" });
    },
    [rfInstance, setInteraction],
  );

  const onAddNode = (
    type: "InputNode" | "OutputNode" | "FunctionNode",
    data: InputDataElement | OutputDataElement | NodeData,
  ) => {
    if (!rfInstance || !contextMenuPos) {
      return;
    }
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

    if (pendingConnection) {
      const { nodeId, handleId, handleType, annotation } = pendingConnection;
      setPendingConnection(null);

      const pickHandle = (
        ports: Annotation[],
        matchDatatype: string | null | undefined,
      ): string | null => {
        if (ports.length === 0) return null;
        if (matchDatatype) {
          const idx = ports.findIndex((p) => p.datatype === matchDatatype);
          if (idx >= 0) return ports[idx].label ?? idx.toString();
        }
        return ports[0]?.label ?? "0";
      };

      let edgeSource: string;
      let edgeSourceHandle: string;
      let edgeTarget: string;
      let edgeTargetHandle: string;

      if (handleType === "source") {
        edgeSource = nodeId;
        edgeSourceHandle = handleId;
        edgeTarget = newId;
        if (type === "OutputNode") {
          edgeTargetHandle = "input";
        } else if (type === "FunctionNode") {
          const nodeData = data as NodeData;
          const h = pickHandle(nodeData.metadata.inputs, annotation?.datatype);
          if (!h) return;
          edgeTargetHandle = h;
        } else {
          return; // InputNode has no target handles
        }
      } else {
        edgeTarget = nodeId;
        edgeTargetHandle = handleId;
        edgeSource = newId;
        if (type === "InputNode") {
          edgeSourceHandle = "output";
        } else if (type === "FunctionNode") {
          const nodeData = data as NodeData;
          const h = pickHandle(nodeData.metadata.outputs, annotation?.datatype);
          if (!h) return;
          edgeSourceHandle = h;
        } else {
          return; // OutputNode has no source handles
        }
      }

      setEdges((es) =>
        addEdge(
          {
            source: edgeSource,
            sourceHandle: edgeSourceHandle,
            target: edgeTarget,
            targetHandle: edgeTargetHandle,
          },
          es,
        ),
      );
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

  const displayEdges = useMemo(
    () =>
      edges.map((e) => {
        const compat = highlightState.edgeCompatibility.get(e.id) ?? "unknown";
        const stroke =
          compat === "type-mismatch"
            ? "var(--color-destructive)"
            : compat === "unit-mismatch"
              ? "var(--color-warning)"
              : undefined;
        const dimmed =
          highlightState.activeEdgeIds !== null &&
          !highlightState.activeEdgeIds.has(e.id);
        return {
          ...e,
          style: {
            ...e.style,
            ...(stroke ? { stroke } : {}),
            opacity: dimmed ? 0.1 : 1,
          },
        };
      }),
    [edges, highlightState.edgeCompatibility, highlightState.activeEdgeIds],
  );

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
        edges={displayEdges}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onConnectStart={onConnectStart}
        onConnectEnd={onConnectEnd}
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
            setPendingConnection(null);
            setIsAddNodeDialogOpen(false);
          }}
          onAdd={onAddNode}
          initialSearchQuery={
            pendingConnection?.annotation?.label ?? undefined
          }
          initialFilter={
            pendingConnection
              ? ({
                  category: null,
                  type: null,
                  author: null,
                  keywords: null,
                  datatypes: pendingConnection.annotation?.datatype
                    ? [pendingConnection.annotation.datatype]
                    : null,
                  units: pendingConnection.annotation?.unit
                    ? [pendingConnection.annotation.unit]
                    : null,
                  quantities: pendingConnection.annotation?.quantity
                    ? [pendingConnection.annotation.quantity]
                    : null,
                  port_type:
                    pendingConnection.handleType === "source"
                      ? "inputs"
                      : "outputs",
                } satisfies Filter)
              : undefined
          }
          connectingHandleType={pendingConnection?.handleType}
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
