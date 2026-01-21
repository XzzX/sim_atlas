import { useCallback, useRef, useState } from 'react';
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
  reconnectEdge,
  type OnConnectStart,
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
import { HighlightHandleContext } from './HighlightHandleContext';

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

  const edgeReconnectSuccessful = useRef(true);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(layoutedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutedEdges);
  const [isImportDialogOpen, setIsImportDialogOpen] = useState(false);
  const [isAddNodeDialogOpen, setIsAddNodeDialogOpen] = useState(false);
  const [contextMenuPos, setContextMenuPos] = useState<{ x: number; y: number } | null>(null);
  const [dialogInitialFilters, setDialogInitialFilters] = useState<Partial<FilterState>>({});
  const [pendingConnection, setPendingConnection] = useState<Handle | null>(null);
  const [highlightHandle, setHighlightHandle] = useState<Partial<FilterState> | undefined>(undefined);

  const get_port_annotation = (rfInstance: ReactFlowInstance | null, nodeId: string, handleId: string, handleType: 'source' | 'target'): Annotation | null => {
    if (!rfInstance) return null;

    const node = rfInstance.getNode(nodeId);
    if (!node) return null;
    const data = node.data as NodeResponse;
    const io_ports = handleType == 'source' ? data.outputs : data.inputs;
    const annotation: Annotation = io_ports[handleId];
    return annotation;
  }

  const is_connection_type_correct = (source_annotation: Annotation | null, target_annotation: Annotation | null): boolean => {
    if (!source_annotation || !target_annotation) {
      return true;
    }
    if (source_annotation.datatype && source_annotation.datatype !== target_annotation.datatype) {
      return false;
    }
    if (source_annotation.unit && source_annotation.unit !== target_annotation.unit) {
      return false;
    }
    if (source_annotation.quantity && source_annotation.quantity !== target_annotation.quantity) {
      return false;
    }

    return true;
  }

  const onConnect = useCallback(
    (params: Connection) => {
      const source_annotation = get_port_annotation(rfInstance, params.source, params.sourceHandle ?? '', 'source');
      const target_annotation = get_port_annotation(rfInstance, params.target, params.targetHandle ?? '', 'target');

      const edge: Edge = {
        id: `e${params.source}.${params.sourceHandle ?? ''}-${params.target}.${params.targetHandle ?? ''}`,
        source: params.source,
        target: params.target,
        sourceHandle: params.sourceHandle,
        targetHandle: params.targetHandle,
        style: is_connection_type_correct(source_annotation, target_annotation) ? {} : {
          strokeWidth: 2,
          stroke: '#FF0072',
        }
      }
      setEdges((eds) => addEdge(edge, eds));
    },
    [setEdges, rfInstance],
  );

  const onConnectStart: OnConnectStart = useCallback(
    (event, params) => {
      if (!rfInstance) return;

      const node = rfInstance.getNode(params.nodeId);
      if (!node) return;
      const data = node.data as NodeResponse;
      const io_ports = params.handleType == 'source' ? data.outputs : data.inputs;
      const annotation: Annotation = io_ports[params.handleId];

      const filter: FilterState = {
        datatype: annotation.datatype,
        unit: annotation.unit,
        quantity: annotation.quantity,
        // If coming from an output, look for nodes with matching inputs
        // If coming from an input, look for nodes with matching outputs
        filterType: params.handleType == 'source' ? 'inputs' : 'outputs',
      };
      setHighlightHandle(filter);
    },
    [rfInstance],
  );

  const onConnectEnd = useCallback(
    (_: React.MouseEvent | React.TouchEvent, connectionState: FinalConnectionState) => {
      setHighlightHandle(undefined);

      if (connectionState.isValid) {
        // let the built-in onConnect handle the connection if we ended on a handle
        return;
      }
      if (!rfInstance) return;

      setContextMenuPos(rfInstance.screenToFlowPosition({ x: connectionState.to.x, y: connectionState.to.y }));

      const io_ports = connectionState.fromHandle?.type == 'source' ? connectionState.fromNode.data.outputs : connectionState.fromNode.data.inputs;
      const annotation: Annotation = io_ports[connectionState.fromHandle?.id || ''];

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
          };
          setEdges([...edges, newEdge])
          setPendingConnection(null);
        }
      }
    },
    [contextMenuPos, nodes, rfInstance, setNodes],
  );

  const onReconnectStart = useCallback(() => {
    edgeReconnectSuccessful.current = false;
  }, []);

  const onReconnect = useCallback((oldEdge: Edge, newConnection: Connection) => {
    edgeReconnectSuccessful.current = true;
    setEdges((els) => reconnectEdge(oldEdge, newConnection, els));
  }, []);

  const onReconnectEnd = useCallback((_: MouseEvent, edge: Edge) => {
    if (!edgeReconnectSuccessful.current) {
      setEdges((eds) => eds.filter((e) => e.id !== edge.id));
    }

    edgeReconnectSuccessful.current = true;
  }, []);

  return (
    <HighlightHandleContext value={highlightHandle}>
      <ReactFlow
        nodeTypes={nodeTypes}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onReconnect={onReconnect}
        onReconnectStart={onReconnectStart}
        onReconnectEnd={onReconnectEnd}
        onConnect={onConnect}
        onConnectStart={onConnectStart}
        onConnectEnd={onConnectEnd}
        isValidConnection={isValidConnection}
        onInit={setRfInstance}
        selectionMode={SelectionMode.Partial}
        onPaneContextMenu={onPaneContextMenu}
        defaultEdgeOptions={{
          'markerEnd': {
            'type': 'arrowclosed',
            'width': 20,
            'height': 20,
          }
        }}
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
      </ReactFlow >
    </HighlightHandleContext>
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
