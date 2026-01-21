import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import FlowWithProvider from './App.tsx'
import { fetchWorkflow } from './interfaces/NodeStore.ts';
import { convertWorkflow } from './workflow_converter.ts';
import type { Node, Edge } from '@xyflow/react';



const fetchInitialNodesAndEdges = async (): Promise<{ nodes: Node[]; edges: Edge[] }> => {
  const urlSearchString = window.location.search;

  const params = new URLSearchParams(urlSearchString);
  const wf_hash = params.get('wf_hash');
  if (!wf_hash) return { nodes: [], edges: [] };
  const source_code = await fetchWorkflow(wf_hash);
  const { nodes, edges } = convertWorkflow(source_code)
  return { nodes, edges };
}

const { nodes, edges } = await fetchInitialNodesAndEdges();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <FlowWithProvider initialNodes={nodes} initialEdges={edges} />
  </StrictMode>,
)
