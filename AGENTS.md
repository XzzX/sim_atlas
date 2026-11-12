# sim_atlas

Search and discovery platform for simulation nodes (Python functions, workflow definitions, flowrep nodes including pyiron_workflow's) used in scientific computing.

## Repository Layout

```
sim_atlas/
├── backend/    Python: FastAPI REST API + MCP server (sim-atlas-backend)
├── frontend/   TypeScript: React search/browse UI (sim-atlas-frontend)
├── web_ide/    TypeScript: React Flow visual workflow editor (simflow)
├── toolkit/    Python: client-side parsers + uploader (sim-atlas-toolkit)
├── models/     Python: shared REST wire models (sim-atlas-models)
├── api_schema/ TypeScript: zod schemas generated from the backend's OpenAPI (sim-atlas-api-schema, private)
└── docs/       Architecture docs and ADRs
```

## Package Relationships

- `toolkit` parses locally installed Python packages and pushes metadata to `backend`
- `frontend` and `web_ide` are built as static assets and served by `backend` at `/` and `/ide` respectively
- `toolkit` depends on `python-workflow-definition` (shared workflow schema)
- `models` is the single definition of the wire schema shared by `backend` and `toolkit`, released in lockstep and pinned exactly (`sim-atlas-models==<version>`, path source for development); request models forbid server-owned fields (ADR-0024)
- `api_schema` holds the zod schemas and types of the REST API for `frontend` and `web_ide` (`"file:../api_schema"` dependency), generated from the backend's OpenAPI schema and committed (ADR-0027). Never edit `api_schema/src/gen/`: change the Pydantic model, run `scripts/gen-api-schema`, commit the result; CI fails when it is stale

## Architecture & Design Decisions

See [docs/architecture.md](docs/architecture.md) for system overview and data flow.
See [docs/adr/](docs/adr/) for all architectural decision records.

## Environment Configuration

Backend reads config via `pydantic-settings`, from a `.env` file or TOML config files
(`/etc/sim_atlas_config.toml`, `~/.sim_atlas_config.toml`, `.sim_atlas_config.toml`).

**Zero-config to start**: only a JWT secret is schema-required, and `uv run sim-atlas`
auto-generates one plus writes a TOML config file in the working directory on first run if
none exists. No manual setup is needed to start the server or use the public read/search
endpoints.

**Optional, feature-gated**: an LLM API key (OpenAI-compatible) enables docstring enrichment in the toolkit (it is not a backend setting); configuring an embedding provider enables semantic search. Each provider is a package extra (`sim-atlas[fastembed]`, the documented default, or `[openai]` / `[voyageai]`, which also need an API key). Without a configured and installed provider, the backend runs fine with keyword-only search.

Write access (uploading nodes) requires a JWT token: `sim-atlas-access-token`.
