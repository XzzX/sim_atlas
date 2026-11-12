---
status: accepted
date: 2026-11-12
deciders: Sebastian Eibl
scope: [backend, frontend, web-ide]
---

# Generate the TypeScript API schemas from the backend's OpenAPI schema

## Context and Problem Statement

After ADR-0024 the Python wire schema has one definition (`sim-atlas-models`). The two web
apps still had their own hand-written zod copies (`frontend/src/types/index.ts`,
`web_ide/src/interfaces/BackendSchema.ts`), and those had drifted. The web IDE's `Reference`
had no `count` or `artifact_type`. The frontend called `WfDefinition` `WorkflowDefinition`.
Both defined a `NodeMetadata` with an `embedding` field that the API never returns. Neither
knew about `hash` or `packages`. This was the last part of the consequence in ADR-0021 that a
field had to be added once per package, by hand, in four places. This ADR resolves it.

Both apps validate every response at runtime with zod 4 (`*Schema.parse(response.data)`), so
they need zod schemas, not only TypeScript types. How should the apps get them without a
second definition next to the Pydantic models?

## Considered Options

* Generate zod schemas from the backend's OpenAPI schema into one shared, private package
* Generate from the JSON Schema of `sim_atlas_models` alone
* Keep the hand-written copies and add a test that compares them with the backend

## Decision Outcome

Chosen option: **generate from the backend's OpenAPI schema** into `api_schema/`, a private
npm package (`sim-atlas-api-schema`, `"private": true`, never published). Both apps depend on
it with `"file:../api_schema"`. Pydantic stays the only source of truth.

The workflow is: change the Pydantic model, run `scripts/gen-api-schema`, commit the result.

### Why codegen here, when ADR-0024 rejected it

ADR-0024 rejected codegen for the toolkit because both consumers were Python: a shared
package does the same job without a generator, and generated Python fits neither pyright
strict nor the generic base classes. Neither argument holds here. The consumers are
TypeScript, so there is no shared runtime to put a package into. The generated code is
TypeScript that only has to type-check and validate, not fit a class hierarchy.

### Source: `app.openapi()`, not `sim_atlas_models`

The apps also need models that exist only in the backend: `Filter`, `FilterOptions`,
`SearchRequest`, `ScoredSearchResponse`, `Suggestion`, `ExecutionResultMetadata`. Only the
OpenAPI schema has all of them. `scripts/gen-api-schema` builds it in-process from
`sim_atlas.main:app` (no running server; a placeholder JWT secret stops settings loading from
writing a config file). It writes it with sorted keys so that diffs stay small and stable,
and pins `info.version` to `"0"` so that a release, which only bumps the version, does not
make the snapshot stale.

FastAPI's `separate_input_output_schemas` keeps its default (`True`). FastAPI only splits a
model into `-Input`/`-Output` schemas when its validation and serialization JSON Schemas
differ. Today none do, because ADR-0024 already made request and response distinct models. If
a model ever gains, for example, a computed field, the default makes the names change and the
apps stop type-checking, which is loud. With `False`, the response schema would silently lack
the field and zod would strip it from every response.

### Generator: `@hey-api/openapi-ts` (zod plugin), pinned exactly

Evaluated against the schema of this API:

| Requirement | `@hey-api/openapi-ts` 0.99.0 | `orval` 8.47.0 | `openapi-zod-client` 1.18.3 |
|---|---|---|---|
| zod 4 output | yes (default target) | yes | no, depends on zod `^3.19` |
| Named component schemas | yes | no, inlines each schema into each operation | yes |
| `WfNode` as `z.discriminatedUnion` | yes, for a named union (see below) | no, `z.union` | not evaluated (zod 3) |
| `additionalProperties: false` → strict | through a resolver hook (see below) | no | not evaluated |
| `anyOf [X, null]` → `.nullable()`/`.nullish()`, defaults kept | yes | yes | not evaluated |
| Enum values usable as `ArtifactType.workflow` | `ArtifactTypeSchema.enum` | yes | not evaluated |

`orval` was rejected because every endpoint gets its own inlined copy of each schema, so
there would be no `NodeResponseSchema` to share, and because it emits neither strict objects
nor discriminated unions. `openapi-zod-client` targets zod 3.

Two gaps in `@hey-api/openapi-ts`, both closed without patching it:

* It emits `z.discriminatedUnion` only for a union that is a named component. It drops the
  discriminator of the inline union that Pydantic emitted for `WfDefinition.nodes`. `WfNode`
  is therefore a PEP 695 `type` alias in `sim_atlas_models`, which Pydantic emits as a named
  `$defs` entry. This raises the Pydantic floor of `models` and `toolkit` to 2.10, the first
  release that supports `type` aliases. `typing_extensions.TypeAliasType` would work from
  Pydantic 2.5, but it adds a runtime dependency, and ruff's `UP040` rewrites it to the `type`
  statement anyway.
* Its zod 4 object resolver ignores `additionalProperties: false`. A `$resolvers.object` hook
  in `api_schema/openapi-ts.config.ts` emits `z.strictObject` for those objects.

Its configuration keeps the Pydantic names (`NodeResponseSchema`, type `NodeResponse`;
`IOValue`, not `IoValue`) and skips per-operation aliases. The apps pick the schema per
endpoint in `services/api.ts` and keep that hand-written HTTP client.

### Request and response stay distinct

As in ADR-0024, request schemas are strict (`z.strictObject`, an unknown or server-owned key
fails) and response schemas strip unknown keys (zod's default). Client-owned models nested in
a response (`WfDefinition`, its nodes and edges, `PackageRef`, `IOValue`) stay strict there
too, matching their `extra="forbid"` in Python.

### Committed output plus drift check, not generated at build time

`api_schema/openapi.json` and `api_schema/src/gen/` are committed. The CI job `api-schema`
runs `scripts/gen-api-schema` and fails when anything under `api_schema/` changes. It runs
whenever `models/`, `backend/` or `api_schema/` changes. Generating at build time would make
every `npm ci`/`npm run build` (the node CI jobs, `scripts/build`, a frontend-only
contributor) need Python, uv and the backend environment. With committed output they need
none, and a schema change shows up in review as a diff of the generated zod code.

### One shared `file:` package, not generated into each app

Both apps import from `sim-atlas-api-schema`. Generating into each app would mean two
generated copies, two drift checks, and the apps could disagree on their generator version.
npm workspaces were not introduced, because the apps' own `package-lock.json`s, CI caches and
`scripts/build` stay as they are.

The package ships TypeScript sources (`exports` points at `src/index.ts`); the apps' Vite
builds compile them. npm installs a `file:` directory as a symlink, so both apps set
`preserveSymlinks` (in `tsconfig.app.json` and `vite.config.ts`). The files then stay under
the app's `node_modules`. TypeScript then treats them as an external library, so the apps'
`composite` projects accept them. Their `zod` import also resolves to the app's own copy, so
a bundle never contains two zod copies. `zod` is an optional peer dependency of
`api_schema`, so installing the generator there never installs a second zod.

`api_schema/fixtures/workflow-node-response.json` is a real `NodeResponse` of a workflow with
`uses`, `used_by`, port `connections` and `wf_definition`. Both apps parse it with the
generated schema in their tests. It is produced by `backend/tests/test_api_schema_fixture.py`
through the HTTP API, and that test fails when the committed file is stale.

### Consequences

* Good: the TypeScript schemas cannot drift from the Pydantic models without CI failing.
  A field is added once, in `sim_atlas_models` or the backend.
* Good: stricter generated types caught real gaps. The frontend forwarded any `artifact_type`
  from the URL to `/search` (now only valid values), and the test fixtures lacked `hash`,
  `packages` and `Suggestion.keywords`.
* Good: the node CI jobs and `scripts/build` still need no Python.
* Bad: a model change is a two-step change (edit, then regenerate), and contributors who
  forget get a red CI job instead of a working build.
* Bad: a new pinned dev dependency (`@hey-api/openapi-ts`) with its own release cadence; its
  `$resolvers` hook is the part most likely to change between versions.
* Bad: Pydantic floor 2.10 for `models` and `toolkit` (was 2.5/2.7 on Python 3.12, 2.8 on
  3.13).
* Neutral: ADR-0021's consequence of four hand-maintained schema copies is resolved; that ADR
  stays as accepted.
