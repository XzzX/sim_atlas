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

Backend reads config via `pydantic-settings`, from a `.env` file or TOML config files
(`/etc/sim_atlas_config.toml`, `~/.sim_atlas_config.toml`, `.sim_atlas_config.toml`).

**Zero-config to start**: only a JWT secret is schema-required, and `uv run sim-atlas`
auto-generates one plus writes a TOML config file in the working directory on first run if
none exists. No manual setup is needed to start the server or use the public read/search
endpoints.

**Optional, feature-gated**: an LLM API key (OpenAI-compatible) enables docstring enrichment and the agent; configuring an embedding provider enables semantic search (for cloud providers like VoyageAI/OpenAI this also requires an API key). Without an embedding provider configured, the backend runs fine with keyword-only search.

Write access (uploading nodes) requires a JWT token: `sim-atlas-access-token`.
