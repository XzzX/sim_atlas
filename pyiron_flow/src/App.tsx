import { useCallback, useState } from 'react';
import {
  ReactFlow,
  addEdge,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
  useNodesState,
  useEdgesState,
  MiniMap,
  Background,
  useReactFlow,
  getOutgoers,
  ReactFlowProvider,
  Panel,
  type ReactFlowInstance,
  SelectionMode,
} from '@xyflow/react';
import { Button } from "@/components/ui/button"
import "./globals.css";
import './App.css';

import dagre from '@dagrejs/dagre';

import WorkflowNode from "./components/workflow-node";
import { initialNodes, initialEdges } from './initialElements';
import { ImportDialog } from './components/ImportDialog';
import { AddNodeDialog } from './components/AddNodeDialog';
import { convertWorkflow } from './workflow_converter';
import { type NodeResponse } from './components/NodeResponse';

const nodeTypes: NodeTypes = {
  WorkflowNode: WorkflowNode,
};

function Flow() {
  const { getNodes, getEdges, getNodesBounds } = useReactFlow();

  const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
    const dagreGraph = new dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: 'LR' });

    nodes.forEach((node) => {
      dagreGraph.setNode(node.id, getNodesBounds([node]));
    });

    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const newNodes = nodes.map((node) => {
      const { width, height } = getNodesBounds([node])
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

    return { nodes: newNodes, edges };
  };

  const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
    initialNodes,
    initialEdges,
  );

  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [isAddNodeDialogOpen, setIsAddNodeDialogOpen] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState<{ x: number; y: number } | null>(null);

  const onConnect = useCallback(
    (params: Connection) => { setEdges((eds) => addEdge(params, eds)); },
    [],
  );

  const isValidConnection = useCallback(
    (connection: Edge | Connection) => {
      // we are using getNodes and getEdges helpers here
      // to make sure we create isValidConnection function only once
      const nodes = getNodes();
      const edges = getEdges();
      const target = nodes.find((node) => node.id === connection.target);
      const hasCycle = (node: Node, visited = new Set<string>()): boolean => {
        if (visited.has(node.id)) return false;

        visited.add(node.id);

        for (const outgoer of getOutgoers(node, nodes, edges)) {
          if (outgoer.id === connection.source) return true;
          if (hasCycle(outgoer, visited)) return true;
        }

        return false;
      };

      if (!target || target.id === connection.source) return false;
      return !hasCycle(target);
    },
    [getNodes, getEdges],
  );

  const onExport = useCallback(() => {
    if (rfInstance) {
      const flow = rfInstance.toObject();
      console.log(JSON.stringify(flow));
    }
  }, [rfInstance]);

  const onLayout = useCallback(
    () => {
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        nodes,
        edges,
      );

      setNodes([...layoutedNodes]);
      setEdges([...layoutedEdges]);
    },
    [nodes, edges],
  );

  const onImport = useCallback(
    (text: string) => {
      const { nodes, edges } = convertWorkflow(text);
      setNodes(nodes);
      setEdges(edges);

    },
    [setNodes, setEdges],
  );

  const onPaneContextMenu = useCallback(
    (event: React.MouseEvent) => {
      // Prevent default context menu
      event.preventDefault();

      // Check if click is on empty space (not on a node or edge)
      if (event.target === event.currentTarget) {
        if (rfInstance) {
          const { x, y } = rfInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY });
          setContextMenuPos({ x, y });
          setIsAddNodeDialogOpen(true);
        }
      }
    },
    [rfInstance],
  );

  const onAddNode = useCallback(
    (nodeData: NodeResponse) => {
      if (contextMenuPos && rfInstance) {
        const newId = String(Math.max(...nodes.map(n => parseInt(n.id) || 0), 0) + 1);
        const newNode: Node = {
          id: newId,
          data: nodeData,
          position: { x: contextMenuPos.x, y: contextMenuPos.y },
          type: 'WorkflowNode',
        };
        setNodes([...nodes, newNode]);
        setContextMenuPos(null);
      }
    },
    [contextMenuPos, nodes, rfInstance, setNodes],
  );

  return (
    <ReactFlow
      nodeTypes={nodeTypes}
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      isValidConnection={isValidConnection}
      onInit={setRfInstance}
      selectionMode={SelectionMode.Partial}
      onPaneContextMenu={onPaneContextMenu}
      fitView
    >
      <Background />
      {/* <Controls>
        <ControlButton onClick={() => alert('Something magical just happened. ✨')}>
          A
        </ControlButton>
      </Controls> */}
      <MiniMap />
      <Panel position="top-right">
        <Button className="outline" onClick={onLayout}>
          layout
        </Button>
        <Button onClick={onExport}>
          export
        </Button>
        <Button onClick={() => { setIsImportDialogOpen(true); }}>
          import
        </Button>
      </Panel>
      <ImportDialog
        isOpen={isImportDialogOpen}
        onClose={() => { setIsImportDialogOpen(false); }}
        onLoad={onImport}
      />
      <AddNodeDialog
        isOpen={isAddNodeDialogOpen}
        onClose={() => { setIsAddNodeDialogOpen(false); }}
        onAdd={onAddNode}
      />
    </ReactFlow>
  );
}

function FlowWithProvider() {
  return (
    <ReactFlowProvider>
      <Flow />
    </ReactFlowProvider>
  );
}

export default FlowWithProvider;
