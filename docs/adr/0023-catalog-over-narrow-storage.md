---
status: accepted
date: 2026-09-29
deciders: Sebastian Eibl
scope: backend
---

# Catalog module for discovery over a persistence-only StorageInterface

## Context and Problem Statement

ADR-0004 put storage behind `StorageInterface` so the backend "is fully replaceable without
touching the API layer", with MongoDB as the planned successor. Over time the interface grew
to fifteen abstract methods: besides CRUD it declared `search`, `search_semantic`,
`search_hybrid`, `suggest`, `get_filter_options`, `enrich` and `embed_missing`. The only
adapter, `FileSystemStorage`, was 689 lines, of which about 100 were persistence; the rest
was facet filtering, BM25 and RRF ranking, type-ahead tiers, the `used_by`/`connections`
workflow references and embedding orchestration.

So the seam ADR-0004 promised sat in the wrong place. A second adapter would have had to
reimplement the whole search engine, and every search change touched the storage module.
Tests reached the ranking only through the adapter, substituting the embedding provider by
monkeypatching attributes of `file_system_storage`. `search_semantic` had no production
caller left after ADR-0018.

## Considered Options

* Keep search in `StorageInterface`; share code between adapters through a base class.
* Move discovery into a `Catalog` module that reads through a persistence-only
  `StorageInterface`.

## Decision Outcome

Chosen option: **a `Catalog` module (`sim_atlas/catalog/`) over a narrowed
`StorageInterface`**.

* `StorageInterface` keeps node and execution-result CRUD and gains two methods:
  `nodes()` (every stored node, read-only) and `update_nodes()` (a bulk replace, used to
  write embeddings in one save). It no longer knows about search.
* `Catalog` owns `read_node` (hydrated), `search` (keyword), `search_hybrid` (with the
  ADR-0018 keyword fallback), `suggest` (ADR-0020), `get_filter_options`, `enrich` and
  `embed_missing`. REST read routes, the AI routes and the MCP tools (ADR-0019) depend on
  `Catalog` via `get_catalog`; write routes still depend on `StorageInterface` via
  `get_storage`.
* `WorkflowGraph` (the derived `used_by`/`connections` references) moves into the catalog
  and is rebuilt on each read call rather than cached, so the catalog does not need to
  observe writes that go straight to storage.
* `search_semantic` is removed.

### Consequences

* Good, because a new storage adapter implements only persistence (the file-system one is
  now ~180 lines), which is what ADR-0004 intended.
* Good, because ranking, filtering and hydration have one home and one test file
  (`tests/test_catalog.py`), and the storage contract tests cover persistence only.
* Neutral, because each read call rebuilds the workflow graph: one pass over the workflows
  per request, down from the earlier per-hit scans but more than a cached index would cost.
  Caching can come back if the catalog grows enough to notice.
* Neutral, because `Catalog` still calls the module-level `create_embedding` and
  `load_settings`; putting the embedding provider behind its own seam is a separate
  decision.
