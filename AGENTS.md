# sim_atlas

Search and discovery platform for simulation nodes (Python functions, workflow definitions, pyiron nodes) used in scientific computing.

## Repository Layout

```
sim_atlas/
├── backend/    Python: FastAPI REST API + MCP server (sim-atlas-backend)
├── frontend/   TypeScript: React search/browse UI (sim-atlas-frontend)
├── web_ide/    TypeScript: React Flow visual workflow editor (simflow)
├── toolkit/    Python: client-side parsers + uploader (sim-atlas-toolkit)
└── docs/       Architecture docs and ADRs
```

## Package Relationships

- `toolkit` parses locally installed Python packages and pushes metadata to `backend`
- `frontend` and `web_ide` are built as static assets and served by `backend` at `/` and `/ide` respectively
- `backend` depends on `python-workflow-definition` (shared schema, also used by `toolkit`)

## Architecture & Design Decisions

See [docs/architecture.md](docs/architecture.md) for system overview and data flow.
See [docs/adr/](docs/adr/) for all architectural decision records.

## Environment Configuration

Backend reads config from a `.env` file via `pydantic-settings`. Required variables:
- JWT secret key (for write access)
- LLM API key (OpenAI-compatible endpoint)
- VoyageAI API key (embeddings)

Generate an access token with: `sim-atlas-access-token`
