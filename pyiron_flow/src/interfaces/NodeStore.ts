import type { NodeResponse } from './NodeResponse';

async function fetchNodesList(): Promise<NodeResponse[]> {
    try {
        const response = await fetch('http://localhost:8000/nodes/list', {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json() as NodeResponse[];
        return data;
    } catch (error) {
        console.error('Error fetching nodes list:', error);
        throw error;
    }
}

export function findByPythonImport(nodes: NodeResponse[], python_import: string): NodeResponse {
    const filtered_nodes = nodes.find((node) => node.python_import === python_import);

    if (!filtered_nodes) {
        throw new Error(`Node with python_import "${python_import}" not found.`);
    }

    return filtered_nodes;
}

export const nodes = await fetchNodesList();