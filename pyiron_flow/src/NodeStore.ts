import type { NodeResponse } from './components/NodeResponse';

async function fetchNodesList(): Promise<NodeResponse[]> {
    try {
        const response = await fetch('http://localhost:8000/nodes/list', {
            method: 'POST',
        });
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching nodes list:', error);
        throw error;
    }
}

export const nodes = await fetchNodesList();