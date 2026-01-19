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
  type FinalConnectionState,
  type OnConnectStartParams,
  Handle,
} from '@xyflow/react';
import { Button } from "@/components/ui/button"
import "./globals.css";
import './App.css';

import dagre from '@dagrejs/dagre';

import FunctionNode from "./components/FunctionNode";
import { initialNodes, initialEdges } from './initialElements';
import { ImportDialog } from './components/ImportDialog';
import { AddNodeDialog } from './components/AddNodeDialog';
import { convertWorkflow } from './workflow_converter';
import { type NodeResponse, type Annotation } from './interfaces/NodeResponse';
import { annotationMatchesFilter, type FilterState } from './interfaces/FilterState';

const nodeTypes: NodeTypes = {
  WorkflowNode: FunctionNode,
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
  const [dialogInitialFilters, setDialogInitialFilters] = useState<Partial<FilterState>>({});
  const [pendingConnection, setPendingConnection] = useState<Handle | null>(null);

  const onConnect = useCallback(
    (params: Connection) => { setEdges((eds) => addEdge(params, eds)); },
    [setEdges],
  );

  const onConnectEnd = useCallback(
    (_: React.MouseEvent | React.TouchEvent, connectionState: FinalConnectionState) => {
      if (connectionState.isValid) {
        // let the built-in onConnect handle the connection if we ended on a handle
        return;
      }
      console.log(connectionState)

      if (!rfInstance) return;

      setContextMenuPos(rfInstance.screenToFlowPosition({ x: connectionState.to.x, y: connectionState.to.y }));

      const io_ports = connectionState.fromHandle?.type == 'source' ? connectionState.fromNode.data.outputs : connectionState.fromNode.data.inputs;
      const annotation: Annotation = io_ports[connectionState.fromHandle?.id || ''];

      console.log(io_ports)
      console.log(annotation)

      const filter: FilterState = {
        datatype: annotation.datatype,
        unit: annotation.unit,
        quantity: annotation.quantity,
        // If coming from an output, look for nodes with matching inputs
        // If coming from an input, look for nodes with matching outputs
        filterType: connectionState.fromHandle?.type == 'source' ? 'inputs' : 'outputs',
      };
      setDialogInitialFilters(filter);
      setPendingConnection(connectionState.fromHandle);
      setContextMenuPos(rfInstance.screenToFlowPosition({ x: connectionState.to.x, y: connectionState.to.y }));
      setIsAddNodeDialogOpen(true);
    },
    [rfInstance],
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
          setContextMenuPos(rfInstance.screenToFlowPosition({ x: event.clientX, y: event.clientY }));
          setDialogInitialFilters({});
          setPendingConnection(null)
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

        if (pendingConnection) {
          const io_ports = pendingConnection.type == 'source' ? nodeData.inputs : nodeData.outputs;
          const filtered_ports = Object.entries(io_ports).find(([, v]) => annotationMatchesFilter(v, dialogInitialFilters));
          if (!filtered_ports) {
            return;
          }

          const newEdge: Edge = {
            id: `e${pendingConnection.nodeId}.${pendingConnection.id}-${newId}.${pendingConnection.type === 'source' ? 'input' : 'output'}`,
            source: pendingConnection.type === 'source' ? pendingConnection.nodeId : newId,
            target: pendingConnection.type === 'source' ? newId : pendingConnection.nodeId,
            sourceHandle: pendingConnection.type === 'source' ? pendingConnection.id : filtered_ports[0],
            targetHandle: pendingConnection.type === 'source' ? filtered_ports[0] : pendingConnection.id,
            markerEnd: {
              type: 'arrowclosed',
              width: 20,
              height: 20,
            },
          };
          setEdges([...edges, newEdge])
          setPendingConnection(null);
        }
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
      onConnectEnd={onConnectEnd}
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
        onClose={() => {
          setIsAddNodeDialogOpen(false);
          setDialogInitialFilters({});
        }}
        onAdd={onAddNode}
        initialFilters={dialogInitialFilters}
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
