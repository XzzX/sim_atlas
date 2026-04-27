---
status: accepted
date: 2026-04-27
deciders: Sebastian Eibl
scope: backend
---

# Inject catalog filter options into the agent system prompt

## Context and Problem Statement

The workflow-builder agent calls `search_nodes` and `find_compatible_nodes` with faceted
filter arguments such as `datatypes`, `units`, `quantities`, and `keywords`. These arguments
must be drawn from the finite set of values that actually exist in the node catalog — there
is no point filtering on `unit="kelvin"` when the catalog only uses `"K"`. Without
knowing the valid values the model must guess, which produces two failure modes:

1. **Hallucinated filter values** — the model writes a plausible-sounding value that does
   not match any stored port metadata, silently returning zero results.
2. **Overly broad queries** — the model avoids filters altogether because it is unsure of
   the correct vocabulary, reducing search precision.

The backend already computes the full set of valid filter values at read time via
`StorageInterface.get_filter_options()`, so the data is cheaply available.

## Considered Options

* **A — Inject into the system prompt**: call `get_filter_options()` once at the start of
  each agent request and append the resulting value lists to the system prompt as a
  "Available filter values" section.
* **B — Add a `get_filter_options` tool**: expose a new tool that the agent can call on
  demand to retrieve valid filter values before applying a filter.
* **C — Enum fields in tool schemas**: build the `TOOLS` list dynamically so that
  `datatypes`, `units`, `quantities`, and `keywords` parameters carry `"enum": [...]`
  constraints that the model cannot violate.

## Decision Outcome

Chosen option: **A — Inject into the system prompt**, because it provides the information
unconditionally with zero extra LLM round-trips and without the reliability risk of the
model needing to decide when to call an additional tool.

### Consequences

* Good, because the model sees all valid filter values before writing its first tool call,
  preventing hallucinated values without any extra round-trips.
* Good, because `get_filter_options()` is a pure in-memory scan — the overhead is
  negligible compared to the network round-trip to the LLM.
* Good, because the values are accurate at request time: if the catalog grows between
  server restarts the fresh values are included automatically.
* Neutral, because the system prompt grows by roughly 50–300 tokens depending on catalog
  diversity. For typical catalogs this is insignificant relative to the full context.
* Bad, because very large catalogs with hundreds of distinct units or datatypes could make
  the list unwieldy. If this becomes a problem the list can be capped or summarised in a
  follow-up decision.

## Rejected Options

**Option B** wastes a full LLM round-trip whenever the agent uses filters (which is
frequently), and relies on the model reliably choosing to call the tool before filtering —
an assumption that is not guaranteed.

**Option C** provides a hard constraint that prevents invalid values, but `"enum"` fields
in JSON Schema can cause models to skip filtering entirely when no listed value seems like a
perfect match, reducing recall. The schema must also be rebuilt per request (or at least at
startup), and newly added catalog values would not be reflected until the server restarts.
