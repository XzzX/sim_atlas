import type { NodeResponse } from './NodeResponse';

export async function fetchWorkflow(wf_hash: string): Promise<string> {
    try {
        const response = await fetch(`http://localhost:8000/nodes/${wf_hash}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data?.source_code ?? '';
    } catch (error) {
        console.error('Error fetching workflow:', error);
        throw error;
    }
}

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
console.log('Fetched nodes:', nodes);