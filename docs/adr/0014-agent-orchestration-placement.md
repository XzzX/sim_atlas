---
status: accepted
date: 2026-04-27
deciders: Sebastian Eibl
scope: cross-cutting
---

# Agent Orchestration Placement

## Context and Problem Statement

The Web IDE provides an AI agent that helps users build simulation workflows by searching the
node catalog and proposing graph mutations. The agent runs a tool-calling loop against an
OpenAI-compatible LLM and emits incremental graph operations over SSE.

The system must support two distinct deployment modes:

* **Private / single-user** — deployed locally on a researcher's machine; a single
  operator-configured LLM API key is acceptable.
* **Public / multi-user** — deployed on the internet (or a shared HPC login node); multiple
  independent users must each use their own LLM credentials; no operator-level API key should
  be charged per user request.

Additional requirements that shape the decision:

* Users may want to run a **local model** (e.g. Ollama) for data-sovereignty or privacy
  reasons, requiring a custom `api_url` alongside the key.
* The agent endpoint is also exposed as an **MCP tool** (see ADR-0008), so
  non-browser clients (Copilot, Claude, automation scripts) must be able to reach it.
* Future work includes **multi-turn conversation**: the agent maintains message history
  across several user turns, not just a single request.
* The backend already handles **direct storage access** inside the tool-calling loop
  (`search_nodes`, `find_compatible_nodes`, `get_node_details`) without additional HTTP
  round-trips.

## Considered Options

* **A — Server-side agent, server-supplied credentials**: orchestration fully in the backend;
  `llm_api_key`, `llm_api_url`, and `llm_chat_model` come from server environment variables.
* **B — Server-side agent, client-supplied credentials**: orchestration stays in the backend;
  the caller passes `llm_api_key`, `llm_api_url`, and `llm_chat_model` in the request body;
  the backend uses them for that request only and never persists them.
* **C — Client-side agent**: the tool-calling loop moves entirely into the browser; the
  frontend calls the LLM directly, translates tool calls into REST calls to the backend, and
  assembles graph mutations locally.

## Decision Outcome

Chosen option: **B — Server-side agent, client-supplied credentials**, because it satisfies
all deployment modes without duplicating the orchestration logic and without exposing secrets
beyond what HTTPS already protects.

The `AgentRequest` model gains **one** optional field — the API key:

```python
class AgentRequest(BaseModel):
    query: str
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    llm_api_key: str | None = None   # overrides settings.llm_api_key
```

**Neither the base URL nor the model is client-supplied.** Both always come from
`settings.llm_base_url` and `settings.llm_chat_model`.

For the base URL this is a security decision: forwarding a caller-controlled URL would let
anyone use this unauthenticated endpoint to probe the server's internal network (SSRF), and
the available mitigations — an HTTPS-only rule, or an operator allowlist — both add
configuration surface for a capability nobody has asked for yet.

For the model it is a scope decision: the operator provisions one model per deployment, and
pinning it keeps the request contract to a single field. Since the model is fixed, the
question of a half-filled credential pair — and the `model_validator` that would have guarded
it — disappears.

Accepting a caller-supplied URL behind an operator allowlist, and a caller-supplied model,
both remain open as follow-up work. Until then, users who want a different provider or model
configure it on the server (which for a single-user local deployment they own anyway).

Note that the field named `llm_api_url` in earlier drafts of this ADR never existed; the
setting is `llm_base_url`.

Credential resolution lives in `resolve_llm_config()` in `agent/_runner.py`, which the route
calls **before** the `StreamingResponse` starts — once the response headers are flushed, the
`AINotConfiguredError` handler can no longer produce a 503. A caller key wins over the server
key; a caller key cannot substitute for a missing server-side base URL or model. Keys are
never logged or stored.

The `/agent/stream` route is registered unconditionally. It used to be created only when
`settings.agent_enabled` was true at import time, which meant a server without an operator key
had no endpoint for a bring-your-own-key user to call at all.

`GET /capabilities` reports `agent_enabled` (the server alone can run the agent) alongside
`llm_base_url` and `llm_chat_model` (both non-null means bring-your-own-key is possible, and
the dialog displays them read-only so the user knows which provider their key must be for).
The Web IDE always renders the agent panel and uses these values to decide between the message
composer and a "configure your LLM" call to action.

In **private mode** the field need not be sent — the server configuration is used as-is and
the settings dialog can be left untouched.

In **public mode** the frontend presents a settings dialog where users enter their key once;
it is stored in `localStorage` and attached to every agent request.

Multi-turn conversation is handled by retaining the `messages` list in the frontend between
turns and including it in subsequent `AgentRequest` payloads (see ADR-0016).

### Consequences

* Good, because a single backend implementation serves both private and public deployments
  with no code branching.
* Good, because credentials travel only over HTTPS and are discarded after each request —
  the server never becomes a credential store.
* Good, because the MCP interface continues to work: MCP callers supply their own key in the
  request body just as the browser does.
* Good, because direct storage access inside the tool-calling loop is preserved — no
  extra HTTP round-trips per tool call.
* Good, because keeping the base URL server-side means the endpoint cannot be turned into an
  SSRF vector.
* Neutral, because pinning the model server-side keeps the request contract to one field, at
  the cost of users not being able to choose a model.
* Neutral, because the frontend must collect and manage per-user credentials; this adds a
  small settings UI to the Web IDE.
* Bad, because credentials appear in the HTTP request body and therefore in access logs
  unless log sanitisation is applied — an operator responsibility in public deployments.
* Bad, because a key held in `localStorage` is readable by any XSS on the origin. Accepted:
  the key is transmitted to the backend on every request regardless, so `localStorage` widens
  the exposure window rather than creating a new class of exposure, and the alternative
  (re-entry on every page load) was judged not worth the friction.

## Pros and Cons of the Options

### A — Server-side agent, server-supplied credentials

* Good, because no credential management is required on the client side.
* Good, because the backend is simple: one set of env vars, no request-level credential
  handling.
* Bad, because in a public deployment all users share a single API key — costs are
  uncontrollable and attribution is impossible.
* Bad, because users cannot use their own local model without access to the server
  environment.
* Bad, because the operator bears the cost and risk of every user's agent invocation.

### B — Server-side agent, client-supplied credentials (chosen)

* Good, because each user is responsible for their own LLM costs and credentials.
* Good, because the orchestration logic, storage access, and MCP surface remain in the
  backend unchanged.
* Neutral, because per-user credential handling adds a small settings UI.
* Bad, because credentials must be sanitised from access logs in public deployments.
* Bad, because choosing a different provider (e.g. a local Ollama) or a different model still
  requires server access, since neither is client-supplied.

### C — Client-side agent

* Good, because API keys never leave the user's machine — the strongest possible
  credential isolation.
* Good, because each user's model choice is entirely self-contained.
* Bad, because every tool call (search, node lookup) becomes a REST round-trip to the
  backend, adding latency inside the agent loop.
* Bad, because the orchestration logic must be re-implemented in TypeScript, duplicating
  the Python backend and diverging over time.
* Bad, because the MCP surface is lost: non-browser callers would have no agent to call.
* Bad, because the LLM API key is visible in browser developer tools and network traffic,
  even if not sent to the backend server.
* Bad, because multi-turn conversation state is lost on page reload with no straightforward
  server-side recovery path.
