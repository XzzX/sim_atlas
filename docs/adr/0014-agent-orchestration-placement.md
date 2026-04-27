---
status: draft
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

The `AgentRequest` model gains three optional fields:

```python
class AgentRequest(BaseModel):
    query: str
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    llm_api_key: str | None = None   # falls back to settings.llm_api_key if absent
    llm_api_url: str | None = None   # falls back to settings.llm_api_url if absent
    llm_chat_model: str | None = None  # falls back to settings.llm_chat_model if absent
```

The runner constructs the `AsyncOpenAI` client from the request fields, falling back to
server-configured values when they are absent. Keys are never logged or stored.

In **private mode** none of the fields need to be sent — the server env vars take precedence
and the UI can hide the credentials panel entirely.

In **public mode** the frontend presents a settings panel where users enter their credentials
once; the values are stored in `localStorage` and attached to every agent request. Users who
prefer a local model supply an Ollama (or equivalent) URL instead of an API key.

Multi-turn conversation is handled by retaining the `messages` list in the frontend between
turns and including it in subsequent `AgentRequest` payloads (a `history` field to be added
in a follow-up ADR).

### Consequences

* Good, because a single backend implementation serves both private and public deployments
  with no code branching.
* Good, because credentials travel only over HTTPS and are discarded after each request —
  the server never becomes a credential store.
* Good, because the MCP interface continues to work: MCP callers supply their own credentials
  in the request body just as the browser does.
* Good, because local-model users supply their own `llm_api_url` (e.g.
  `http://localhost:11434/v1`) without any server reconfiguration.
* Good, because direct storage access inside the tool-calling loop is preserved — no
  extra HTTP round-trips per tool call.
* Neutral, because the frontend must collect and manage per-user credentials; this adds a
  small settings UI to the Web IDE.
* Neutral, because `llm_api_url` is a user-supplied URL; the backend should validate it
  against an allowlist or restrict to HTTPS in public deployments to mitigate SSRF risk.
* Bad, because credentials appear in the HTTP request body and therefore in access logs
  unless log sanitisation is applied.

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
* Good, because local-model users only need to configure a URL in the UI — no server
  access required.
* Neutral, because per-user credential handling adds a small settings UI.
* Bad, because credentials must be sanitised from access logs in public deployments.

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
