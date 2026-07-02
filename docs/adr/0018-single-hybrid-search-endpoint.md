---
status: accepted
date: 2026-07-01
deciders: Sebastian Eibl
scope: backend
supersedes: 0008-mcp-semantic-search.md
---

# Single auto-hybrid search endpoint with keyword fallback

## Context and Problem Statement

The backend exposed three search routes: `POST /api/v1/search` (keyword-only),
`POST /api/v1/semantic_search`, and `POST /api/v1/hybrid_search`. The latter two had
byte-for-byte identical bodies (both called `storage.search_hybrid`), forcing every caller
to choose a mode it often could not validate. Worse, `search_hybrid` called the embedding
provider unconditionally, so with no embeddings configured the semantic/hybrid routes
returned **503** — a search endpoint that fails because AI is off. Parameters were also split
awkwardly across the query string (`query`, `page`, `limit`) and the JSON body (`filter`).

## Considered Options

* Keep three endpoints, just fix the 503 by adding a fallback inside `search_hybrid`.
* Collapse to a single `POST /api/v1/search` endpoint that auto-selects the strategy.

## Decision Outcome

Chosen option: **a single `POST /api/v1/search` endpoint** driven by a typed `SearchRequest`
body (`query`, `filter`, `semantic`, `page`, `limit`).

* It performs hybrid (semantic + keyword RRF) search when embeddings are configured
  (`Settings.embeddings_enabled`) and silently falls back to keyword-only otherwise — search
  always works, never 503.
* An optional `semantic` flag preserves control: `null`/omitted = auto, `true` = prefer
  hybrid, `false` = force keyword-only even when AI is available.
* The fallback lives in `storage.search_hybrid`, so the agent tools benefit too.
* Both search paths return the same fields (`used_by` is populated in the hybrid path as
  well as the keyword path).
* The single route carries `operation_id="search_nodes"` and is the sole MCP search tool,
  replacing the `semantic_search`/`hybrid_search` operations from ADR 0008.

### Consequences

* Good, because clients no longer pick a mode they cannot validate; the server decides based
  on its own capabilities.
* Good, because search degrades gracefully instead of returning 503 without embeddings.
* Good, because one typed request body yields a cleaner OpenAPI/MCP schema and validated
  pagination bounds (`limit` capped at 100).
* Bad, because it is a breaking API change: `/semantic_search` and `/hybrid_search` are
  removed and all clients (frontend, web_ide, e2e) must post the new body shape.
