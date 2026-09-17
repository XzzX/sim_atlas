---
status: accepted
date: 2026-09-17
deciders: Sebastian Eibl
scope: [backend, frontend]
---

# A separate, cheap type-ahead suggest endpoint

## Context and Problem Statement

The search page does two different jobs with one request. While the user types, a dropdown under
the search box should show a fast list of partial title matches. Once they pause, the results table
below should run the full hybrid (semantic + keyword) search. Today both are served by
`POST /api/v1/search`: the frontend derives the dropdown from the same response that fills the
table (`SearchPage.tsx`), so the dropdown cannot appear before a full hybrid search has returned —
including a query-embedding network round-trip when an embedding provider is configured — and it is
capped at one page of hybrid-ranked results rather than ranked by title match.

Feeding the dropdown from `/search` is also inherently the wrong cost. Both `search` and
`search_hybrid` run a post-pagination enrichment loop (`_used_by`, `_fill_connections`) that is
`O(limit · P · N · (V+E))` in the catalog size — quadratic work to populate `used_by` references and
port-to-port connections, none of which a navigational dropdown needs — and that loop mutates the
stored artifacts in place. A per-keystroke lookup cannot afford this, no matter how the ranking is
tuned.

Separately, `keyword_search.rank` (BM25) matches whole tokens only, so a query issued while the user
is still mid-word (`"temp"` against `get_temperature`) matches nothing until the word is finished.
This is fixed alongside the endpoint (trailing-token prefix expansion in the shared ranker), so the
results table also behaves correctly mid-word, not only the new dropdown.

## Considered Options

* **A — Keep deriving suggestions from `POST /search`**, just render sooner: fix nothing at the
  request level.
* **B — Add a `suggest_only` flag to `SearchRequest`**, short-circuiting the enrichment loop inside
  the existing route.
* **C — A separate `POST /api/v1/suggest` endpoint**, sharing the `Filter` vocabulary but matching
  only artifact name and import path, with no enrichment.
* **D — A client-side prefix index**, shipping enough of the catalog to the browser to filter
  in-memory.

## Decision Outcome

Chosen option: **C — a separate `/suggest` endpoint**, POST like `/search` (so the same `Filter`
model binds cleanly — six of its seven fields are lists, and a GET would need either a hand-rolled
query-array convention or an undocumented client-side serialisation), returning a small
`list[Suggestion]` (`id`, `name`, `python_import`, `artifact_type`, `short_description`).

Five properties define the decision:

* **Identifier-only matching.** Only `name` and `python_import` are searched — never docstrings,
  descriptions or embeddings. This is a title lookup for navigation, not a ranked-relevance search.
* **The same filters as `/search`.** The dropdown and the table describe the same scope: a user who
  has filtered to `category=physics` should not be offered a suggestion the table would then fail to
  show. `Filter` is threaded through unmodified rather than invented anew.
* **No enrichment, no mutation.** `suggest` never calls `_used_by` or `_fill_connections`, and never
  writes to a stored artifact — the property that makes it fast enough to run on every keystroke.
* **No pagination.** `limit` is capped at 25 (vs. 100 for `/search`) — this is a dropdown, not a
  result set to page through.
* **Not an MCP tool.** ADR-0019's curated surface serves a CLI coding agent choosing what to import;
  a UI type-ahead has no equivalent need, so `suggest` carries no `operation_id` and is never
  registered with FastMCP.

This departs from ADR-0018, which collapsed three search routes into one and called it "the sole MCP
search tool." That decision removed a choice of *ranking mode* for one question a caller could not
validate (keyword vs. semantic vs. auto). `/suggest` answers a different question — a cheap
identifier lookup for navigation — not a fourth ranking mode, so it does not supersede 0018.

On the frontend, `SearchPage.tsx` gains a second, independently debounced request path (150 ms,
against the existing 500 ms for `/search`) with its own stale-response guard, so a fast keystroke
burst cannot have its dropdown state clobbered by an older in-flight response. Selecting a
suggestion navigates straight to `/node/<id>` — the dropdown is a jump-to-node navigator, not a
query builder, so `SearchBar` never re-filters what the server already matched
(`filter={null}` on the Base UI `Autocomplete`).

### Consequences

* Good, because the dropdown becomes O(match count) string work instead of a graph walk that scales
  with the whole catalog, and can genuinely run on every keystroke.
* Good, because the two panels can never disagree about scope — same `Filter`, same active facets.
* Good, because the ranker fix (trailing-token prefix expansion) benefits `/search` and the MCP
  tools too, not just the new endpoint.
* Neutral, because the catalog now exposes two search-family routes where ADR-0018 deliberately left
  one; the distinction (ranked relevance vs. identifier lookup) is the thing to preserve if either
  evolves.
* Bad, because `Suggestion` is a fourth artifact-adjacent model hand-mirrored across
  Python/TypeScript with no codegen (ADR-0019 already flags this cost for `PackageRef`).

## Pros and Cons of the Options

### A — Keep deriving from `/search`

* Good, because no new route, no new model, no new frontend request path.
* Bad, because the dropdown inherits `/search`'s full cost (embedding round-trip, enrichment loop)
  no matter how it is rendered — the problem is the request, not the UI.

### B — A `suggest_only` flag on `SearchRequest`

* Good, because it reuses the existing route and model.
* Bad, because it makes one route do two structurally different jobs (ranked relevance vs.
  identifier lookup) behind a boolean, which is exactly the ambiguity ADR-0018 removed for
  `semantic` — trading one unvalidatable flag for another.
* Bad, because the response shape would need to vary by flag anyway (full artifact vs. a thin
  suggestion), so little is actually shared beyond the URL.

### C — A separate `/suggest` endpoint (chosen)

* Good, because the route's cost model matches its job: no enrichment, no embedding call, ever.
* Good, because a thin, purpose-built response model is easy to reason about and cheap to serialise.
* Neutral, because it is a second search-family route to keep behaviourally consistent with the
  first (same `Filter` semantics).
* Bad, because two routes must be kept in sync if the artifact identity fields they expose change.

### D — A client-side prefix index

* Good, because it would need no network round-trip at all once loaded.
* Bad, because it requires shipping catalog identifiers to the browser up front and keeping them
  fresh as the catalog changes — a caching and staleness problem with no clear owner.
* Bad, because it does not honour `Filter` without also shipping the filterable fields, at which
  point most of the catalog has been sent to the client regardless of size.
