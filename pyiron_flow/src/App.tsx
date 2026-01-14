import React, { useCallback } from 'react';
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
  Controls,
  Background,
  MarkerType,
  useReactFlow,
  getOutgoers,
  ReactFlowProvider,
} from '@xyflow/react';
import "./globals.css";
import './App.css';

import WorkflowNode from "./components/workflow-node";

const initialNodes: Node[] = [
  {
    id: '1',
    data: { label: 'Input Node' },
    position: { x: 0, y: 0 },
    type: 'WorkflowNode',
  },
  {
    id: '2',
    data: { label: 'Process Node' },
    position: { x: 250, y: 100 },
    type: 'WorkflowNode',
  },
  {
    id: '3',
    data: { label: 'Output Node' },
    position: { x: 500, y: 0 },
    type: 'WorkflowNode',
  },
];

const initialEdges: Edge[] = [
  {
    id: 'e1-2', source: '1', sourceHandle: 'source-1', target: '2', targetHandle: 'target-1', markerEnd: {
      type: MarkerType.ArrowClosed, width: 20,
      height: 20,
    }
  },
  { id: 'e2-3', source: '2', sourceHandle: 'source-1', target: '3', targetHandle: 'target-1', markerEnd: { type: MarkerType.ArrowClosed } },
];

const nodeTypes: NodeTypes = {
  WorkflowNode: WorkflowNode,
};

function Flow() {
  const { getNodes, getEdges } = useReactFlow();

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
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

  return (
    <ReactFlow
      nodeTypes={nodeTypes}
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      // isValidConnection={isValidConnection}
      fitView
    >
      <Background />
      <Controls />
      <MiniMap />
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
