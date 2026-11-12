# frontend

React SPA for searching and browsing simulation nodes. Deployed as static assets served by the backend at `/`.

## Commands

```bash
npm run dev          # dev server (Vite, port 5173)
npm run build        # production build → dist/
npm run lint         # ESLint (zero warnings policy)
npm run type-check   # tsc --build --noEmit
```

## Key Patterns

- **API calls**: all HTTP requests go through `services/api.ts` (Axios); do not call `fetch` directly
- **UI components**: reusable primitives live in `components/ui/` (shadcn-style, Base UI + Tailwind); use those before adding new dependencies
- **Routing**: React Router; pages live in `pages/`
- **API types**: import API schemas and types from `sim-atlas-api-schema` (`../api_schema`), generated from the backend's Pydantic models; never define them by hand or edit `api_schema/src/gen/`: change the Pydantic model, run `scripts/gen-api-schema`, commit the result (ADR-0027). `services/api.ts` parses every response with the matching `*Schema`; keep only UI-specific types local
- **Styling**: Tailwind CSS v4; use utility classes, not inline styles
- **Build output**: `dist/` is copied into backend's static directory — do not commit `dist/`
