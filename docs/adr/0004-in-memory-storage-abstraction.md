---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: backend
---

# In-memory storage behind a StorageInterface abstraction

## Context and Problem Statement

The backend must persist `NodeMetadata` objects and support basic CRUD and search
operations. In the early phase of the project, setting up and operating a database adds
infrastructure overhead that would slow down iteration. At the same time, swapping in a
persistent backend later must not require changes to the API layer.

## Considered Options

* In-memory dict wrapped in a `StorageInterface` abstraction
* MongoDB

## Decision Outcome

Chosen option: **in-memory storage behind `StorageInterface`**, because the current number
of registered nodes is well within what fits in memory, and the abstraction makes the
backend fully replaceable without touching the API layer. MongoDB is the planned successor
once performance or persistence requirements demand it; the switch will be triggered by
hitting observable performance problems rather than by speculation.

The `StorageInterface` class (`backend/app/storage.py`) extends
`MutableMapping[str, NodeMetadata]`, so any future backend needs only to implement the same
mapping protocol.

### Consequences

* Good, because the backend starts with zero external dependencies — `uv run` is sufficient.
* Good, because the abstraction boundary means the API layer, search logic, and AI enrichment
  code are completely decoupled from the storage implementation.
* Bad, because all data is lost on process restart; the system must be re-populated after
  every restart.
* Neutral, because migrating to MongoDB requires implementing `StorageInterface` and wiring
  it up at startup — a well-scoped change that does not affect callers.

## Pros and Cons of the Options

### In-memory storage

* Good, because zero infrastructure — no database process to run or configure.
* Good, because reads and writes are O(1) in-process operations with no serialisation overhead.
* Good, because trivial to reset to a clean state for testing.
* Bad, because data does not survive process restarts.
* Bad, because does not scale beyond a single process (no horizontal scaling).

### MongoDB

* Good, because data is durable across restarts.
* Good, because horizontal scaling and replication are built in.
* Good, because the document model fits `NodeMetadata` naturally (schema-flexible JSON).
* Good, because atlas-vector-search or a similar feature could eventually replace the
  in-process cosine similarity implementation.
* Bad, because requires running and operating a MongoDB instance (or a managed service),
  adding infrastructure overhead.
* Bad, because introduces network latency on every read/write compared to in-process access.
