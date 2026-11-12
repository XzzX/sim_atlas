---
status: accepted
date: 2026-11-12
deciders: Sebastian Eibl
scope: toolkit
---

# Two-phase parsers driven by a worklist pipeline

## Context and Problem Statement

Each toolkit parser is a single `async def parse(ctx, obj)` that does everything for one
object: it hashes the object, asks the store whether the node exists, builds the request, runs
LLM enrichment and source self-containment, and stores the node. Workflow parsers additionally
re-enter the parser chain for every node they reference, recursively, and read their children
back from the store to describe them.

This makes the parser the place where all I/O and all control flow live:

* **Recursive re-entry.** A child shared by several workflows is parsed, enriched (an LLM call)
  and existence-checked once per parent. Nothing coordinates two parents reaching the same
  child concurrently.
* **Store access in parsers.** Every parser repeats the same existence check, enrichment
  sequence and store call; the store round-trips are one per object, never batched; and
  workflow docstring generation reads children back from the store just after they were
  created.
* **Validation is per store.** Parsers build requests with `model_construct`, and only
  `HttpNodeStore` re-validates them; any other store would accept invalid requests.

## Considered Options

* Keep single-phase parsers; add a shared memo and helper functions they call
* Split parsers into a pure, two-phase contract (`identify` / `describe`) and move all I/O into
  a worklist pipeline

## Decision Outcome

Chosen option: **two-phase parsers and a worklist pipeline**
(`sim_atlas_toolkit.plugin`, `sim_atlas_toolkit.pipeline`).

* A parser is two synchronous, pure methods. `identify(obj)` returns the content-hash id of
  the node the object yields and the objects it references (`children`), or `None` for "not
  mine". `describe(obj, identity, children)` returns the node draft, receiving the children
  that resolved as `ResolvedChild`s. Neither method sees a store, settings or the network.
* **One object, at most one node.** `Identity.node_id` is a single id, or `None` for a
  *container* that yields no node of its own (e.g. a workflow instance that only carries
  execution results). An object that stands for several nodes is modelled as a container
  whose children are those nodes. This makes node id and object identity the same thing for
  deduplication, existence checks and child resolution, and lets every non-container child
  reach its parent as a `ResolvedChild` (children are keyed by label, one node each).
* **Discovery is level-wise with batched existence checks.** The pipeline identifies every new
  object of a level, deduplicates entries by node id, and calls
  `NodeStore.existing_ids` once per level. Only the children of *missing* entries are
  expanded; a container (no node of its own) always counts as missing. Reference cycles are
  detected and reported as errors.
* **Build is children first.** Missing entries are described once all their children are
  finished; independent entries run concurrently under a semaphore. Enrichment
  (`Enrichment.FUNCTION`/`WORKFLOW`/`NONE`) and self-containment run in the pipeline, not in
  the parsers.
* **Validation is at the boundary.** Every draft is validated into a `NodeRequest` (dumping
  nested values by their runtime type) before it reaches any store, and the pipeline checks
  that the described id equals the identified one.

The legacy single-phase path stays in place next to the new one until the cutover.

### Consequences

* Good, because the early-out is preserved and widened: an existing node is never described,
  and an existing workflow's subtree is never visited.
* Good, because a shared child is identified once per object but described, enriched and
  stored once, with existence checks batched per level instead of one per object.
* Good, because parsers become pure functions of their input, testable without a store, and
  workflow docstrings are written from in-memory children instead of store reads.
* Bad, because `identify` carries an obligation the type system cannot enforce: it must be
  cheap (no LLM, no griffe, no I/O beyond imports), since it runs for every reachable object,
  including those that turn out to exist already.
* Neutral, because upload counts now include child nodes (previously only top-level results
  were counted), each child in the group of the first seed that reached it, and objects no
  parser accepts are reported separately as `unparsed` instead of as errors.
* Neutral, because the one-node rule will retire the virtual dataclass PACK/UNPACK pair, the
  only multi-node parser: the legacy dataclass parser keeps emitting it until dataclasses are
  ported as one constructor node (#233). A future parser that
  maps one object to several nodes has to wrap them as a container's children.

## Pros and Cons of the Options

### Single-phase parsers with a shared memo

* Good, because it is a smaller diff.
* Bad, because every parser keeps its own copy of the existence check, enrichment sequence and
  store call, and recursion order stays implicit in the parsers.
* Bad, because existence checks cannot be batched when each parser asks for its own object.

### Two-phase contract and worklist pipeline (chosen)

* Good, because control flow and I/O live in one place, which later steps (an efficient
  `existing_ids` over HTTP, more parsers) build on.
* Bad, because every parser has to be ported, and both paths coexist until the cutover.
