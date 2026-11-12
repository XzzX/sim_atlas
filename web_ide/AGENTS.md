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
- **API calls**: all HTTP requests go through `services/`; do not call `fetch` directly
- **API types**: import API schemas and types from `sim-atlas-api-schema` (`../api_schema`), generated from the backend's Pydantic models; never define them by hand or edit `api_schema/src/gen/`: change the Pydantic model, run `scripts/gen-api-schema`, commit the result (ADR-0027). Only schemas of other formats (e.g. `PythonWorkflowDefinitionSchema.ts`, an import file format) stay local
- **Build output**: `dist/` is copied into backend's static directory — do not commit `dist/`

## Libraries
- **ReactFlow**: [Documentation](https://reactflow.dev/llms.txt)
