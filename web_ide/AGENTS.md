# web_ide

React Flow-based visual workflow editor for composing simulation pipelines. Deployed as static assets served by the backend at `/ide`.

## Commands

```bash
npm run dev          # dev server (Vite)
npm run build        # production build → dist/
npm run lint         # ESLint (zero warnings policy)
npm run type-check   # tsc --build --noEmit
```

## Key Patterns

- **Canvas**: `ReactFlowEditor.tsx` owns the React Flow instance; `MainLayout.tsx` wraps the overall page layout
- **Custom nodes**: all node types live in `nodes/`; extend `base-node.tsx` for new node types
- **Handles**: use `labeled-handle.tsx` for typed connection points; `base-handle.tsx` for unstyled handles — do not use React Flow handles directly
- **Layout**: Dagre (`@dagrejs/dagre`) for automatic graph layout; triggered via layout utilities in `lib/`
- **Workflow schema**: import/export JSON follows the `PythonWorkflowDefinition` format from the `toolkit` package; see `importWorkflow.ts`
- **Agent panel**: `AgentPanel.tsx` integrates with the backend's streaming agent endpoint
- **API calls**: all HTTP requests go through `services/`; do not call `fetch` directly
- **Build output**: `dist/` is copied into backend's static directory — do not commit `dist/`
