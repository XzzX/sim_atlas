---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: backend
---

# File-system-backed storage behind a StorageInterface abstraction

## Context and Problem Statement

The backend must persist `NodeMetadata` objects and support basic CRUD and search
operations. In the early phase of the project, setting up and operating a database adds
infrastructure overhead that would slow down iteration. At the same time, swapping in a
persistent backend later must not require changes to the API layer.

## Considered Options

* In-process dict with pickle persistence wrapped in a `StorageInterface` abstraction
* MongoDB

## Decision Outcome

Chosen option: **file-system-backed storage behind `StorageInterface`**, because the current
number of registered nodes is well within what fits in memory, and the abstraction makes the
backend fully replaceable without touching the API layer. MongoDB is the planned successor
once performance or persistence requirements demand it; the switch will be triggered by
hitting observable performance problems rather than by speculation.

The `StorageInterface` class (`backend/app/storage_interface.py`) extends
`MutableMapping[str, NodeMetadata]`, so any future backend needs only to implement the same
mapping protocol.

`FileSystemStorage` (`backend/app/file_system_storage.py`) is the concrete implementation. It
holds data in an in-process dict and serialises it to a pickle file on every write. The
`filename` constructor parameter controls persistence: passing a file path enables
load-on-startup and save-on-write; passing `None` disables all file I/O (used in tests).

### Consequences

* Good, because the backend starts with zero external dependencies — `uv run` is sufficient.
* Good, because the abstraction boundary means the API layer, search logic, and AI enrichment
  code are completely decoupled from the storage implementation.
* Good, because data survives process restarts via the pickle file.
* Neutral, because migrating to MongoDB requires implementing `StorageInterface` and wiring
  it up at startup — a well-scoped change that does not affect callers.

## Pros and Cons of the Options

### File-system-backed storage

* Good, because zero infrastructure — no database process to run or configure.
* Good, because reads are O(1) in-process operations with no serialisation overhead.
* Good, because data survives process restarts via pickle serialisation.
* Good, because trivial to disable persistence for testing by passing `filename=None`.
* Bad, because write latency includes a full pickle serialisation of the entire dict.
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
