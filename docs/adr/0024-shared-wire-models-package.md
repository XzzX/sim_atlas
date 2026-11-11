---
status: accepted
date: 2026-11-11
deciders: Sebastian Eibl
scope: [backend, toolkit]
---

# Shared wire models in a separate, lockstep-released package

## Context and Problem Statement

The backend (`backend/src/sim_atlas/models.py`) and the toolkit
(`toolkit/src/sim_atlas_toolkit/models.py`) each defined the REST wire schema (`NodeRequest`,
`NodeResponse`, annotations, references, `WfDefinition`, execution results) by hand. Nothing
kept the two copies in sync, and they had already drifted: the backend called the request-side
port annotation `AnnotationRequest`, the toolkit `Annotation`. A field added on one side and
forgotten on the other, or in `compose_node`, was dropped without an error.

The models also did not say who owns a field. `Reference.artifact_type`, `creator_*` and
`used_by` are values the server sets, but nothing stopped a client from sending them. The
backend ignored unknown fields, so a misspelled or outdated field was silently discarded too.

How should the two Python packages share one schema, and how should the schema state which
side owns each field?

## Considered Options

* A separate package `sim-atlas-models` that backend and toolkit both depend on
* The backend depends on the toolkit (or the toolkit on the backend) and imports its models
* Generate the toolkit's models from the backend's OpenAPI schema (codegen)

## Decision Outcome

Chosen option: **a separate package `sim-atlas-models`** (directory `models/`, import name
`sim_atlas_models`). It contains only the shared wire models and depends only on `pydantic`.
Backend-only models (`NodeMetadata`, search, filter and suggest models,
`ExecutionResultMetadata`) stay in the backend.

* A backend/toolkit dependency in either direction was rejected. The toolkit runs on
  researchers' machines and must not pull in FastAPI, numpy and the server stack. The backend
  must not pull in the parsers and their optional dependencies.
* OpenAPI codegen was rejected (see #219). It adds a generator and a build step, the generated
  code fits neither pyright strict nor our generic base classes, and both consumers are Python
  anyway.

### Versioning

`sim-atlas-models` has the same version as `sim-atlas` and `sim-atlas-toolkit` and is
released with them from the same tag. Each dependent pins it exactly
(`sim-atlas-models==<version>`). For development, a `[tool.uv.sources]` path source points at
`../models` (editable); release builds use `uv build --no-sources` and resolve from PyPI.
`scripts/release` bumps all three packages and rewrites the pins. A schema change is then
always released as a matching set, and there is no compatibility matrix to maintain.

### Field ownership

Types enforce field ownership:

| Kind | Fields | In request model? |
|---|---|---|
| client-owned | name, category, keywords, author\_\*, URLs, python_import, dependencies, packages, source_code, docstring, brief_description, description, inputs/outputs (without `connections`), see_also, uses, wf_definition, artifact_type | yes |
| client-owned, server defaults | `id`, `hash` (default `sha256(source_code)`, ADR-0005) | yes, optional |
| server-generated | creator_name, creator_email, creation_timestamp (nodes and execution results), execution result `id` | no |
| server-derived | `used_by`, `AnnotationResponse.connections`, `ReferenceResponse.artifact_type` | no |

* **Request models** (`NodeRequest`, `Annotation`, `Reference`, `ExecutionResultRequest`, and
  the client-owned `Wf*`, `PackageRef`, `IOValue`) use `extra="forbid"`. A request that
  contains a server-owned or unknown field is rejected with 422 instead of silently trimmed.
* **Response models** (`NodeResponse`, `AnnotationResponse`, `ReferenceResponse`,
  `ExecutionResultResponse`) use `extra="ignore"`. They add the server-owned fields and accept
  fields a newer server adds.
* Every shared field is defined once, in a private `_…Fields` base class. The class is generic
  over the annotation and reference type where request and response differ
  (`_NodeFields[AnnT, RefT]`). Redefining fields in subclasses was rejected, because pyright
  strict rejects narrowing overrides (`reportIncompatibleVariableOverride`).
* `Reference` is split into `Reference` (request: `label`, `id`, `count`) and
  `ReferenceResponse` (adds `artifact_type`). Clients can no longer send `artifact_type`, so
  the server derives it from the catalog for `uses` and `see_also` too, not only for `used_by`
  and `connections` (`WorkflowGraph.hydrate`). Like the other derived fields, it is never
  stored. A stored value from older files is dropped on load.
* `compose_node` builds the stored node from the request's dump plus the server fields. A new
  client-owned field therefore reaches storage without changes there.

### Consequences

* Good: a field is defined once for both Python packages, so the backend and toolkit schemas
  cannot drift.
* Good: the types state field ownership. Neither side can set a field the other owns, and
  typos or outdated fields in requests fail loudly.
* Good: `compose_node` no longer lists fields by hand, which removes a silent-drop path.
* Bad: a third package to release, and the PyPI project needs its own trusted publisher.
* Bad: `extra="forbid"` is a breaking change for clients that send server-owned fields.
  Toolkit versions up to 0.0.19 send `uses[].artifact_type` (as `null`), so their workflow
  uploads are rejected by a newer server. The lockstep release covers this only when users
  upgrade the toolkit together with the server.
* Neutral: the OpenAPI schema changes in names (`AnnotationRequest` becomes `Annotation`, new
  `ReferenceResponse`), and request schemas gain `additionalProperties: false`. In
  `NodeResponse`, server-owned fields now follow the client-owned ones, and
  `author_name`/`author_email` carry the request default `"unknown"`, so they are no longer
  listed as required. The JSON values themselves are unchanged.
