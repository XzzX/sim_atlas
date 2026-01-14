import React, { useCallback } from 'react';
import ReactFlow, {
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
} from 'reactflow';
import 'reactflow/dist/style.css';
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
  // { id: 'e1-2', source: '1', sourceHandle: 'source-1', target: '2', targetHandle: 'target-1' },
  // { id: 'e2-3', source: '2', sourceHandle: 'source-1', target: '3', targetHandle: 'target-1' },
];

const nodeTypes: NodeTypes = {
  WorkflowNode: WorkflowNode,
};

function App() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [],
  );

  return (
    <ReactFlow
      nodeTypes={nodeTypes}
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      fitView
    >
      <Background />
      {/* <Controls />
      <MiniMap /> */}
    </ReactFlow>
  );
}

export default App;
