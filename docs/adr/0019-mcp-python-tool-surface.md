---
status: accepted
date: 2026-09-15
deciders: Sebastian Eibl
scope: [backend, toolkit]
---

# MCP as an independent, Python-shaped interface for CLI coding agents

## Context and Problem Statement

Simulation Atlas serves AI clients through one channel: the Web IDE agent (ADR-0014), a server-side
tool-calling loop that emits graph mutations for the React Flow canvas. A second, structurally
different audience has appeared — researchers working in a terminal with a local CLI coding agent
(Claude Code), writing plain Python functions and `@flowrep.workflow`-decorated pipelines.

That audience has properties the Web IDE agent does not share. The agent runs on the user's machine,
so it can import a module, execute it, read the traceback and fix its own output — a verification
loop the browser cannot offer. It owns the local environment, so it can install a missing package.
And it produces Python text, not a graph.

The existing MCP surface (a single `search` tool, the remnant of ADR-0008) does not serve it: it
exposes no filters, no detail lookup and no route to a workflow's source, and it returns whole
artifact records including `source_code`, costing 5–15k tokens for three hits.

Two questions follow. Should the CLI agent be served by the existing Web IDE agent endpoint? And
what shape should the catalog present to a client whose output medium is Python source?

## Considered Options

* **A — Route CLI agents to `POST /api/v1/agent/stream`**: reuse the existing server-side agent.
* **B — Auto-derive MCP tools from the REST routes** (the original ADR-0008 approach).
* **C — A curated, independent, read-only MCP tool surface in Python vocabulary.**
* **D — A dedicated `sim-atlas` CLI for the coding agent to shell out to.**

## Decision Outcome

Chosen option: **C — a curated, independent, read-only MCP tool surface**, co-existing with the Web
IDE agent as a second and fully separate way to interact with Simulation Atlas.

Four tools replace the single `search` tool, named and shaped in Python vocabulary:

| Tool | Purpose |
|---|---|
| `search_functions(query, kind)` | natural-language discovery |
| `find_by_signature(query, datatype, unit, quantity, match)` | port-annotation search — the capability a local agent cannot replicate by grepping `site-packages` |
| `get_function(id)` | full signature, docstring, units, `used_by` |
| `get_workflow_source(id)` | the stored executable Python of a workflow |

Five properties define the decision:

* **Claude Code is the agent.** The server exposes tools and nothing else. Nesting an LLM loop
  behind an LLM loop would add latency, degrade results, and require a server-side LLM key for a
  client that already has one.
* **Output is Python-shaped.** Every hit leads with a reconstructed `def` line, then the import
  statement, then an install hint; everything else is `#`-commented, so the only executable line in
  a result block is the one the agent lifts into the script. The Web IDE's `Inputs:`/`Outputs:` port
  listing stays where it belongs.
* **Read-only.** No upload tool is registered, and every tool carries `readOnlyHint`. Write access
  stays with the authenticated toolkit path, keeping JWTs out of the local agent and unreviewed
  generated workflows out of the catalog.
* **The server is environment-agnostic.** It records which distributions an uploader's environment
  contained (`packages: list[PackageRef]`, pypi and conda, several entries per artifact) and stops
  there. Checking what is importable, choosing the package manager and installing — with user
  confirmation — belong to the local agent, which is the only party that can see the environment.
* **The two surfaces share no code path.** `mcp_server/` does not import from `agent/`. Only one
  four-line text helper (`artifact_text.short_description`) is common. Either surface can be changed
  without regressing the other.

Consistent with ADR-0012, `packages` records what was *observed* in an uploader's environment. The
absence of a conda entry does not mean a package is unavailable on conda-forge, and install hints
reach the user as suggestions to confirm, never as commands to run.

Since artifact identity is the SHA-256 of `source_code` (ADR-0005), the same function uploaded from
a pip environment and a conda environment is one artifact, and the second upload is skipped. Several
ecosystem entries per artifact therefore come from a single environment that has both (a conda-forge
package almost always ships `.dist-info` too), not from merging uploads. A merge-on-duplicate path
is deliberately not built until single-environment coverage proves insufficient.

### Consequences

* Good, because the Web IDE agent is untouched — no shared tool registry, no shared output format,
  no regression surface.
* Good, because token cost per search drops by roughly an order of magnitude: `source_code` leaves
  every search path, and five lean hits cost less than three fat ones.
* Good, because the unit/quantity search that only this catalog can answer is exposed under its own
  tool name, where a model will actually select it, rather than as optional keyword arguments.
* Good, because the server needs no knowledge of local environments, and gains no new failure mode
  from the install feature.
* Neutral, because guidance on *when* to consult the atlas lives in two places — the FastMCP server
  instructions and a shipped skill file — that must be kept consistent.
* Bad, because `packages` is populated only for artifacts uploaded by a toolkit new enough to
  capture it; the whole corpus must be re-uploaded before install hints are useful.
* Bad, because the artifact models are hand-mirrored in three Python/TypeScript locations with no
  codegen, so `PackageRef` must be added by hand in each place that needs it.

## Pros and Cons of the Options

### A — Route CLI agents to the existing agent endpoint

* Good, because no new surface is built and the tool-calling loop is already written and observable.
* Bad, because it puts an LLM behind an LLM: the caller is already a capable agent, and the
  round-trip costs latency, tokens and fidelity.
* Bad, because it emits React Flow graph JSON, which a CLI agent would have to translate into Python
  — a lossy step that the catalog can avoid by returning Python directly.
* Bad, because it requires an LLM key (server-side, or forwarded per ADR-0014) for a client that
  already has its own.

### B — Auto-derive MCP tools from the REST routes

* Good, because tool schemas stay in sync with the API for free.
* Bad, because REST response models are designed for a React SPA: whole artifact records, full
  `source_code`, embeddings-adjacent fields — the exact token problem being fixed.
* Bad, because tool names and descriptions are then derived from route metadata, and tool
  descriptions are prompt text that decides whether the tool is used at all.

### C — Curated, independent, read-only MCP surface (chosen)

* Good, because tool names, descriptions and output are tuned as prompt text for a Python-writing
  agent.
* Good, because read-only plus no shared code path bounds the blast radius of the new surface.
* Neutral, because four hand-written tools must be maintained alongside the REST routes.
* Bad, because a curated surface can drift from the REST API's capabilities if search gains
  features that are not mirrored.

### D — A dedicated CLI for the agent to shell out to

* Good, because it works with any coding agent, not only MCP-capable ones, and is trivially testable
  from a shell.
* Good, because it could inspect the local environment directly.
* Bad, because it requires an install step and a version-compatibility story with the server, where
  MCP needs only a URL.
* Bad, because tool descriptions — the thing that makes a model use the catalog at all — have no
  equivalent in `--help` text that the agent reads only after deciding to run the command.
