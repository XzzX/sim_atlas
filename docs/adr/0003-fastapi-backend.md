---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: backend
---

# Use FastAPI as the backend framework

## Context and Problem Statement

The backend needs to expose a REST API for node registration and search, integrate with an
OpenAI-compatible LLM API for embeddings and enrichment, and serve the built frontend assets
from its own process. The framework must support async I/O, automatic OpenAPI documentation,
and strong Pydantic-based request/response validation.

## Considered Options

* FastAPI

## Decision Outcome

Chosen option: **FastAPI**, because it provides native async support, first-class Pydantic
integration (eliminating a separate validation layer), automatic OpenAPI/Swagger docs, and a
large ecosystem of ASGI middleware. Its type-annotation-driven approach also aligns naturally
with the project's strict Pyright configuration.

Additionally, `fastapi-mcp` — which exposes FastAPI routes as MCP tools — targets FastAPI
specifically (see ADR-0008).

### Consequences

* Good, because request and response models are defined once as Pydantic classes and reused
  across validation, serialization, and OpenAPI docs.
* Good, because async endpoints make LLM API calls non-blocking without extra threading.
* Neutral, because ASGI deployment (Uvicorn/Hypercorn) is required; this is standard for
  modern Python services.
