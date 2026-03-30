# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) for the Simulation Atlas project.
ADRs are written in the [MADR format](https://adr.github.io/madr/) (Markdown Any Decision Records, v3).

## Scope values

Each ADR carries a `scope:` frontmatter field indicating which part(s) of the system the decision affects:

| Value | Description |
|---|---|
| `cross-cutting` | Applies to the whole project or multiple sub-packages |
| `backend` | `backend/` — FastAPI service |
| `frontend` | `frontend/` — React search portal |
| `toolkit` | `toolkit/` — Python ingestion library |
| `web-ide` | `web_ide/` — React Flow workflow editor |

A decision that affects multiple components lists all values, e.g. `scope: [backend, toolkit]`.

## Status values

- **proposed** — under discussion, not yet implemented
- **accepted** — decided and implemented
- **deprecated** — no longer relevant
- **superseded by [ADR-XXXX](XXXX-title.md)** — replaced by a newer decision

## Process

1. Copy the MADR template from ADR-0001.
2. Assign the next consecutive ID.
3. Fill in `status`, `date`, `deciders`, and `scope`.
4. Never edit an accepted ADR in place — create a superseding ADR instead.

## Index

| ID | Title | Status | Scope |
|---|---|---|---|
| [0001](0001-use-madr.md) | Use MADR as Architecture Decision Records format | accepted | cross-cutting |
| [0002](0002-monorepo-structure.md) | Monorepo with four independent sub-packages | accepted | cross-cutting |
| [0003](0003-fastapi-backend.md) | Use FastAPI as the backend framework | accepted | backend |
| [0004](0004-in-memory-storage-abstraction.md) | File-system-backed storage behind a StorageInterface abstraction | accepted | backend |
| [0005](0005-sha256-node-identity.md) | SHA-256 source hash as node identity | accepted | backend, toolkit |
| [0006](0006-on-demand-ai-enrichment.md) | On-demand AI enrichment | accepted | backend |
| [0007](0007-openai-compatible-llm-api.md) | OpenAI-compatible LLM API | accepted | backend |
| [0008](0008-mcp-semantic-search.md) | Expose semantic search as an MCP tool | accepted | backend |
| [0009](0009-static-file-serving.md) | FastAPI serves frontend assets as static files | accepted | backend |
| [0010](0010-react-flow-web-ide.md) | React Flow for the visual workflow editor | accepted | web-ide |
| [0011](0011-metadata-only-storage.md) | Store node metadata with links to external source repositories | accepted | cross-cutting |
| [0012](0012-best-effort-data-quality.md) | Information is provided on a best-effort basis without freshness or correctness guarantees | accepted | cross-cutting |
