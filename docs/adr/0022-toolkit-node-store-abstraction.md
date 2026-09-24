---
status: accepted
date: 2026-09-24
deciders: Sebastian Eibl
scope: toolkit
---

# NodeStore abstraction decouples the toolkit's parser pipeline from HTTP

## Context and Problem Statement

The toolkit's parse/upload pipeline was written directly against `httpx2.Response`: every
parser was typed `-> list[httpx2.Response]`, `orchestrator.py` counted outcomes by comparing
`.status_code` against `HTTPStatus.CREATED`/`CONFLICT`, and a shared `extract_id` helper dug
`id` out of `.json()`. HTTP was therefore not an implementation detail behind an interface but
the pipeline's actual currency — every parser, and the orchestrator itself, spoke HTTP
directly.

This blocks adding a filesystem-only upload path (a local, zero-coordination catalogue for a
single researcher, or an air-gapped/HPC-batch workflow with no reachable backend — the same
motivation ADR-0013 already accepted for the backend's deployment model). Introducing a
second storage target without an abstraction would mean threading two implementations through
every parser by hand.

Two related problems surfaced during the audit that motivated this change:

* The toolkit's `NodeResponse`/`Annotation`/`Reference` models — documented as "a
  hand-maintained mirror of the backend's Pydantic schemas" — had drifted from the backend's
  actual response shape (missing `used_by`, `AnnotationResponse.connections`,
  `Reference.artifact_type`).
* Six parser call sites short-circuited on a `read_node` dedup hit by returning the raw HTTP
  200 response. The orchestrator's counting logic recognized only `CREATED` (201) and
  `CONFLICT` (409), so every deduplicated node was silently counted as an error in the upload
  summary.

## Considered Options

* Keep `httpx2.Response` as the pipeline's currency; add a second, parallel set of
  filesystem-flavored parser entry points
* Introduce a `NodeStore` abstraction (`abc.ABC`, matching the backend's
  `StorageInterface`) and a typed `NodeResult` carrying the same `NodeResponse` model the API
  returns, with `HttpNodeStore` as the sole implementation for now

## Decision Outcome

Chosen option: **`NodeStore` abstraction + typed `NodeResult`**, because it is the same
decision ADR-0004 already made for the backend's storage layer, applied one layer out. Every
parser now receives a `ParseContext` (`settings` + `store`) instead of bare `ToolkitSettings`,
and returns `list[NodeResult]` — a `NodeStatus` (`CREATED`/`EXISTS`) plus the stored
`NodeResponse` — instead of raw HTTP responses. `HttpNodeStore` is the only implementation
today; a future filesystem-backed store only needs to implement the same four-method
interface (`create_node`, `read_node`, `create_execution_result`, `trigger_embed`).

Closing the model-mirror gaps was a prerequisite, not a side effect: once parsers validate
real response bodies into `NodeResponse` at every dedup site (not just the one place that
happened to do so before), a stale mirror becomes a silent-failure surface rather than a
cosmetic inaccuracy.

Fixing the dedup-counted-as-error bug fell out of the same change: a dedup hit is now
represented as `NodeStatus.EXISTS` by construction, which the orchestrator's two-way count
(`CREATED` vs. everything else) can no longer misclassify as an error the way the old
three-way `status_code` comparison did.

### Consequences

* Good, because a `LocalNodeStore` (or any other storage backend) can be added by implementing
  `NodeStore`, without touching any parser.
* Good, because the toolkit's `NodeResponse` mirror is now validated at every dedup site
  instead of just one, making drift from the backend's schema fail loudly during development
  rather than silently dropping fields (pydantic's default `extra="ignore"`).
* Good, because deduplicated nodes are now counted correctly in the upload summary, and
  `upload_modules` returns that summary (`list[ModuleUploadResult]`) instead of only logging
  it — the return value is what let the fix be pinned with a regression test in the first
  place.
* Neutral, because a store failure now aborts the whole object being parsed rather than being
  tallied per-node (only observable for the one parser, `dataclass_node`, that returns two
  nodes per object) — this is the tradeoff of representing failure as an exception rather
  than as a third `NodeStatus` member that would force every consumer to handle a `None` node.
* Neutral, because `read_node` no longer treats every non-200 response as "not a dedup hit,
  upload anyway"; only 404 means absent, anything else raises. A flaky backend now surfaces as
  an error instead of silently falling through to a re-upload the backend would have answered
  with 409 anyway.

## Pros and Cons of the Options

### `NodeStore` abstraction (chosen)

* Good, because it mirrors the backend's own `StorageInterface`/`FileSystemStorage` split
  (ADR-0004), so the toolkit and backend follow the same architectural pattern.
* Good, because the parser contract's semantic surface was always just "status + id" —
  formalizing that as `NodeResult` removes `httpx2.Response` from the type system without
  losing anything parsers actually used.
* Bad, because it touches every parser's signature and every parser-facing test, a large
  mechanical diff.

### Parallel filesystem-flavored parsers

* Good, because it requires no change to the existing HTTP-based parsers.
* Bad, because every parser would need a second implementation (or a manual branch) to support
  local storage, doubling the maintenance surface with every new parser added.
* Bad, because the two paths would drift in behavior (as the model mirror already had),
  with no shared interface to keep them honest.
