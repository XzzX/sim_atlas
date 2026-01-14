import React, { useCallback, useState } from 'react';
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
  ControlButton,
  Panel,
  type ReactFlowInstance,
} from '@xyflow/react';
import "./globals.css";
import './App.css';

import WorkflowNode from "./components/workflow-node";

const initialNodes: Node[] = [
  {
    id: '1',
    data: {
      "author_name": "John Doe",
      "author_email": "john.doe@example.com",
      "node_type": "function",
      "python_import": "my_nodes.sam.get_speed",
      "dependencies": null,
      "source_code": "def get_speed(\n    distance: float,\n    time: float,\n) -> float:\n    speed = distance / time\n    return speed\n",
      "source_code_hash": "5ad2cfd1830c6c1aa9ce88e008056a099e1970d0954408be9914cc154cd496fa",
      "docstring": "",
      "ai_docstring": "",
      "inputs": {
        "distance": {
          "label": null,
          "datatype": "float",
          "unit": null,
          "quantity": null
        },
        "time": {
          "label": null,
          "datatype": "float",
          "unit": null,
          "quantity": null
        }
      },
      "outputs": {
        "return": {
          "label": null,
          "datatype": "float",
          "unit": null,
          "quantity": null
        }
      }
    },
    position: { x: -150, y: 0 },
    type: 'WorkflowNode',
  },
  {
    id: '2',
    data: {
      "author_name": "John Doe",
      "author_email": "john.doe@example.com",
      "node_type": "function",
      "python_import": "my_nodes.sam.get_kinetic_energy",
      "dependencies": null,
      "source_code": "def get_kinetic_energy(\n    mass: float,\n    velocity: float,\n) -> float:\n    return 0.5 * mass * velocity**2\n",
      "source_code_hash": "ce29e7286c653c46872d341a68deec1c4e72f82c8b9b45303429457492ca4514",
      "docstring": "",
      "ai_docstring": "",
      "inputs": {
        "mass": {
          "label": null,
          "datatype": "float",
          "unit": null,
          "quantity": null
        },
        "velocity": {
          "label": null,
          "datatype": "float",
          "unit": null,
          "quantity": null
        }
      },
      "outputs": {
        "return": {
          "label": null,
          "datatype": "float",
          "unit": null,
          "quantity": null
        }
      }
    },
    position: { x: 150, y: 0 },
    type: 'WorkflowNode',
  },

];

const initialEdges: Edge[] = [
  // {
  //   id: 'e1-2', source: '1', sourceHandle: 'source-1', target: '2', targetHandle: 'target-1', markerEnd: {
  //     type: MarkerType.ArrowClosed, width: 20,
  //     height: 20,
  //   }
  // },
  // { id: 'e2-3', source: '2', sourceHandle: 'source-1', target: '3', targetHandle: 'target-1', markerEnd: { type: MarkerType.ArrowClosed } },
];

const nodeTypes: NodeTypes = {
  WorkflowNode: WorkflowNode,
};

function Flow() {
  const { getNodes, getEdges } = useReactFlow();

  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);
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

  const onExport = useCallback(() => {
    if (rfInstance) {
      const flow = rfInstance.toObject();
      console.log(JSON.stringify(flow));
    }
  }, [rfInstance]);

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
      fitView
    >
      <Background />
      <Controls>
        <ControlButton onClick={() => alert('Something magical just happened. ✨')}>
          A
        </ControlButton>
      </Controls>
      <MiniMap />
      <Panel position="top-right">
        <button onClick={onExport}>
          export
        </button>
        {/* <button onClick={onImport}>
          import
        </button> */}
      </Panel>
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
