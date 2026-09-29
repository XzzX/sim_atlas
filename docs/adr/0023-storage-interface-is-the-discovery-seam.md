---
status: accepted
date: 2026-09-29
deciders: Sebastian Eibl
scope: backend
---

# StorageInterface is the discovery seam; backend-independent policy sits above it

## Context and Problem Statement

ADR-0004 put storage behind `StorageInterface` so the backend can be replaced (MongoDB is
the planned successor) without touching callers. The interface declares search as well as
CRUD: `search`, `search_hybrid`, `suggest`, `get_filter_options`. Its only adapter,
`FileSystemStorage`, had grown to 689 lines that mixed persistence, in-process ranking, the
`used_by`/`connections` workflow references, reading settings and calling the embedding
provider.

An architecture review proposed pulling search out into a `Catalog` module over a
persistence-only storage interface. Where should the seam be?

## Considered Options

* **A:** Pull search into a `Catalog` above a persistence-only `StorageInterface`.
* **B:** Keep search in `StorageInterface`; move only backend-independent policy above it,
  and split the in-memory adapter internally.

## Decision Outcome

Chosen option: **B**. The realistic successors to the JSON file, such as MongoDB (Atlas
Search / Vector Search) or Qdrant, search natively: BM25 with field boosts, vector search,
rank fusion, facets and autocomplete. With the seam at the discovery level, each of them is
one adapter that *replaces* our ranking. Option A would put in-process ranking above the
seam, reading every node through a full scan, so a searching database would either be
reduced to a record store or have to route around the catalog.

* `StorageInterface` keeps `search`, `search_hybrid`, `suggest` and `get_filter_options`.
  Every read returns hydrated nodes.
* `search_hybrid(query, query_embedding, ...)` receives the query's embedding. Adapters
  never read settings or call an embedding provider.
* `sim_atlas/discovery.py` holds the policy that is the same for every backend: the
  ADR-0018 choice between hybrid and keyword search, embedding the query, and which nodes
  `enrich`/`embed_missing` embed, from what text. It writes through two batch methods on
  the interface, `nodes()` and `set_embeddings()`.
* `search_semantic` is removed (no production caller since ADR-0018).
* Inside `FileSystemStorage`, ranking lives in `storage/_in_memory_search.py`, facets in
  `storage/_node_filter.py`, and workflow references in `storage/_workflow_graph.py`
  (cached, and invalidated on every node write).

### Consequences

* Good, because a database adapter implements discovery with its own engine, and
  `StorageContractTests` checks every adapter's search against the same behaviour.
* Good, because adapter tests pass query vectors directly; only `discovery` tests
  substitute the embedding provider.
* Neutral, because an adapter's ranking will not match the in-memory BM25 variant exactly
  (field weights, prefix matching on the last word). Contract tests that pin those details
  are the place to decide what a new backend must honour.
* Neutral, because `nodes()` is a full scan. That is fine for batch embedding jobs but is
  not a read path.
