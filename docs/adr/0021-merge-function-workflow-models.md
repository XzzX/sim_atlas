---
status: accepted
date: 2026-09-24
deciders: Sebastian Eibl
scope: [backend, toolkit, frontend, web-ide]
---

# Merge Function\* and Workflow\* artifact models into a single Node\* model

## Context and Problem Statement

Every artifact schema (`models.py` in `backend` and `toolkit`, `types/index.ts` in
`frontend`, `BackendSchema.ts` in `web_ide`) modeled a function and a workflow as two
separate types — `FunctionRequest`/`WorkflowRequest`, `FunctionResponse`/`WorkflowResponse`,
`FunctionMetadata`/`WorkflowMetadata` — joined into a discriminated union
(`ArtifactRequest`/`ArtifactResponse`/`StoredArtifact`) wherever code needed to handle
either. Measured field-by-field, the two sides of each pair were 85-90% identical; a
workflow only adds two fields — `uses` (references to constituent nodes) and
`wf_definition` (its internal dataflow graph) — plus looser optionality on
`python_import`/`docstring`, which functions don't strictly need either (see below).

This duplication had already caused two real defects, not just extra typing:

* `used_by` and per-port `connections` enrichment in `FileSystemStorage` were gated on
  `isinstance(artifact, FunctionMetadata)`, so a workflow referenced inside another
  workflow's `uses` (a nested/sub-workflow) never got a "used by" backlink or port
  connections — the union type made it easy to special-case "the other branch" and forget
  it applies here too.
* `POST /artifacts` generated a workflow's `id` with `uuid4()` while a function's `id` used
  `sha256(source_code)`, contradicting [ADR-0005](0005-sha256-node-identity.md), which
  covers "a Python function or workflow" identically. Every toolkit parser already computed
  `sha256(source_code)` for both cases; the uuid4 branch in `compose_artifact` was simply an
  oversight from having two code paths to keep in sync.

The duplication was also hand-maintained with no codegen across four independent files
(backend, toolkit, and two frontends), so every field addition had to be repeated four
times, and the two React apps had already grown ad-hoc `"used_by" in node` /
`"uses" in node` property-existence checks to work around the union not actually sharing
fields the way the UI needed them to.

## Considered Options

* Keep `Function*`/`Workflow*` as a discriminated union (status quo)
* Merge into a single `Node*` model (`NodeRequest`/`NodeResponse`/`NodeMetadata`) with
  `uses`/`wf_definition` always present, defaulting to empty for a function
* Use inheritance (`WorkflowRequest(FunctionRequest)`) instead of a flat union

## Decision Outcome

Chosen option: **merge into a single `Node*` model**, because the split was not modeling a
real semantic boundary — the two variants are joined into an `ArtifactType` enum field
either way, and `artifact_type` is exactly what the four schema copies already used to tell
them apart at runtime (`ArtifactType.FUNCTION` / `ArtifactType.WORKFLOW`). Keeping one model
with `uses: list[Reference] = []` and `wf_definition: WfDefinition = WfDefinition(nodes=[],
edges=[])` defaulting to empty for a function removes the branching entirely: storage
enrichment (`used_by`, `connections`), `compose_artifact`, and MCP formatting no longer
special-case by type where the underlying operation doesn't actually depend on it.

`python_import` and `docstring` — required on `FunctionRequest`/`FunctionResponse`, optional
on the workflow side — are made optional on the merged model. In practice this was already
close to a fiction: every consumer reads them as `artifact.python_import or ""` (backend
`keyword_search.py`, `file_system_storage.py`, `mcp_server/_format.py`,
`agent/tools/_search.py`), and the toolkit's `python_workflow_definition.py` parser already
stores a workflow-shaped artifact as `FunctionRequest` with `python_import=""` when it
cannot decompose into `wf_definition` (see commit 961ddac). No test or parser relied on
these fields actually rejecting an empty value.

Renaming follows what `backend/CLAUDE.md` already documented ahead of this change — `NodeRequest`
(API write input), `NodeMetadata` (internal storage schema), `NodeResponse` (API read
output) — and what `web_ide/src/interfaces/BackendSchema.ts` had already half-migrated to,
via `NodeRequestSchema = FunctionRequestSchema` backward-compat aliases.

Inheritance (`WorkflowRequest(FunctionRequest)`) was rejected: it still requires two class
names and two branches wherever code constructs or discriminates between them, and doesn't
remove the underlying problem — shared fields living in the base class while workflow-only
fields live in the subclass still forces `isinstance` checks at every "does this apply to
both?" call site, which is exactly what caused the `used_by` bug above.

### Consequences

* Good, because storage enrichment (`used_by`, port `connections`) now applies uniformly,
  fixing the nested-workflow gap described above.
* Good, because `compose_artifact` now generates every artifact's `id`/`hash` the same way
  (`sha256(source_code)`), correcting the ADR-0005 violation.
* Good, because a field addition is made once per package (four total) instead of once per
  package per artifact kind (eight total), and the union-fighting `"x" in node` checks in the
  React apps are gone.
* Good, because `compose_artifact`'s two near-identical branches (60+ lines) collapse to one
  unconditional builder.
* Neutral, because `python_import` and `docstring` becoming optional on a function payload
  is a loosening of the write-side schema; nothing in the codebase depended on the stricter
  version rejecting an empty value (see above), so this is a schema simplification, not an
  observed behavior change.
* Bad, because the OpenAPI schema for `POST /artifacts` changes from a `oneOf` with a
  `artifact_type` discriminator to a single flat object; any external client that generated
  bindings from the old discriminated schema needs regenerating (there are none yet, cf.
  ADR-0011's discoverability-only scope).
