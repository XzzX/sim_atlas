---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: backend
---

# On-demand AI enrichment

## Context and Problem Statement

When a node is registered, useful AI-generated metadata can be produced: a natural-language
docstring and a semantic embedding vector (used for similarity search). Generating these at
upload time would make every registration slow and dependent on LLM API availability.
The question is when to trigger AI enrichment.

## Considered Options

* Generate embeddings and AI docstrings automatically at upload time
* Expose a separate endpoint that must be called explicitly
* Run enrichment asynchronously in a background worker after upload

## Decision Outcome

Chosen option: **separate endpoint**, because it keeps the upload path fast
and deterministic regardless of LLM API availability. It also makes AI costs explicit and
intentional: an operator can choose to enrich all nodes, a subset, or none at all.

The endpoint is idempotent — calling it multiple times simply regenerates the metadata.

### Consequences

* Good, because node registration never fails due to LLM API downtime.
* Good, because operators have full control over when and how much enrichment is performed.
* Good, because the enrichment step is independently retryable.
* Neutral, because nodes without enrichment will have no embedding and will not appear in
  semantic search results until endpoint has been called.

## Pros and Cons of the Options

### Generate embeddings and AI docstrings automatically at upload time

* Good, because every registered node is immediately searchable via semantic search.
* Good, because the caller does not need to know about a separate enrichment step.
* Bad, because a slow or unavailable LLM API blocks the entire upload path.
* Bad, because upload latency becomes unpredictable and dependent on external service
  response times.
* Bad, because AI costs are incurred unconditionally for every upload, including test or
  exploratory registrations.

### Expose a separate endpoint (chosen)

* Good, because node registration is fast and independent of LLM API availability.
* Good, because AI costs are explicit and controllable — operators decide what to enrich
  and when.
* Good, because the enrichment step is independently retryable without re-uploading the node.
* Good, because the endpoint is idempotent, making it safe to call repeatedly (e.g. to
  regenerate metadata with a better model).
* Bad, because newly registered nodes are not semantically searchable until enrichment is
  triggered separately.

### Run enrichment asynchronously in a background worker after upload

* Good, because the upload endpoint returns immediately, like the chosen option.
* Good, because enrichment happens automatically without a separate API call.
* Bad, because requires a task queue (e.g. Celery, ARQ) and a worker process, significantly
  increasing infrastructure complexity.
* Bad, because there is a window after upload during which the node is not yet semantically
  searchable, with no clear signal to the caller about when it will be ready.
* Bad, because failures in the background worker are harder to surface and retry than a
  synchronous endpoint call.
