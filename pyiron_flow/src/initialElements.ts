import {
    MarkerType,
    type Edge,
    type Node,
} from '@xyflow/react';
import { nodes } from './interfaces/NodeStore';

export const initialNodes: Node[] = [
    {
        id: '1',
        data: nodes.find(n => n.python_import === 'my_nodes.sam.get_speed')!,
        position: { x: -150, y: 0 },
        type: 'WorkflowNode',
    },
    {
        id: '2',
        data: nodes.find(n => n.python_import === 'my_nodes.sam.get_kinetic_energy')!,
        position: { x: 150, y: 0 },
        type: 'WorkflowNode',
    },
    {
        id: '3',
        data: nodes.find(n => n.python_import === 'my_nodes.xzzx.calculate_velocity')!,
        position: { x: 150, y: 0 },
        type: 'WorkflowNode',
    },

];

export const initialEdges: Edge[] = [
];