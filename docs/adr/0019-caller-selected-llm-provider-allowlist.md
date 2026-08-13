---
status: accepted
date: 2026-08-13
deciders: Sebastian Eibl
scope: [backend, web-ide]
---

# Caller-selected LLM provider, model and reasoning effort behind an operator allowlist

## Context and Problem Statement

[ADR-0014](0014-agent-orchestration-placement.md) settled on a server-side agent with
client-supplied credentials, but pinned the provider base URL and the chat model to
`settings.llm_base_url` / `settings.llm_chat_model` and left one item explicitly open:

> Accepting a caller-supplied URL behind an operator allowlist, and a caller-supplied model,
> both remain open as follow-up work.

Two needs make that follow-up due:

* Users must be able to choose between more than one endpoint — at minimum the GWDG Academic
  Cloud and OpenAI — and to pick a model, without server access.
* Reasoning models need a `reasoning_effort` control.

The constraint is unchanged and is the crux: `POST /api/v1/agent/stream` is unauthenticated,
and non-browser callers can hit it directly, so whatever the request carries must not turn the
backend into an open proxy or an SSRF vector.

A second problem surfaced while scoping this. ADR-0014's `resolve_llm_config` reads
`request.llm_api_key or settings.llm_api_key`. On a public deployment that has an operator key
configured, **any anonymous caller can already spend it** — up to `agent_max_iterations` LLM
round-trips per request, with no attribution.

## Considered Options

For provider selection:

* **A — Caller sends `llm_base_url`, server validates it against `llm_allowed_base_urls`.**
* **B — Caller sends an opaque provider `id`; the server looks the base URL up in its own
  catalog.**
* **C — Keep the base URL pinned server-side** (status quo from ADR-0014).

For the operator's key:

* **D — Keep the fallback to `settings.llm_api_key`.**
* **E — Remove it: the agent only ever runs on a caller-supplied key.**
* **F — Remove it but add an opt-in escape hatch** (`agent_allow_server_key`) so a local,
  single-user deployment keeps a zero-configuration agent.

For `reasoning_effort` support:

* **G — Forward whatever the caller picked** and let the provider reject it.
* **H — One `reasoning_effort` flag per provider.**
* **I — One flag per model** in the catalog.

## Decision Outcome

Chosen: **B + E + I.**

### B — Provider selection by opaque id

`AgentRequest` gains `llm_provider`, `llm_chat_model` and `llm_reasoning_effort`; it still
carries `llm_api_key`. It never carries a URL.

The operator's allowlist lives in `settings.llm_providers`, modelled in
`backend/src/sim_atlas/llm_providers.py`:

```toml
[[llm_providers]]
id = "gwdg"
label = "GWDG Academic Cloud"
base_url = "https://chat-ai.academiccloud.de/v1/"
models = ["qwen3.6-27b"]

[[llm_providers]]
id = "openai"
label = "OpenAI"
base_url = "https://api.openai.com/v1"
models = [
    { name = "gpt-5", label = "GPT-5", reasoning_effort = true },
    "gpt-4.1",
]
```

`resolve_llm_config()` looks the id up and takes the `base_url` from the catalog entry, so **no
caller-supplied string ever reaches the HTTP client**. This is the decisive advantage over
option A: with a validated URL, the comparison itself becomes security-critical and has to
survive trailing-slash, case, userinfo, IDN and percent-encoding variations, plus whatever
`httpx` would do with a redirect. An id lookup has no such surface — a caller who sends
`http://169.254.169.254/` as the provider gets a 400 naming the two allowed ids, and nothing is
dialled.

Selecting outside the allowlist raises the new `LLMSelectionError`, mapped to **400**. Its
message enumerates what *is* allowed and never echoes the rejected value, so the endpoint cannot
be used to reflect attacker-controlled content.

Setting `llm_providers` in a config file **replaces** the built-in GWDG + OpenAI defaults rather
than extending them; `CONFIG_TEMPLATE` ships the defaults commented out so extending is a
copy-paste. A `requires_api_key = false` entry supports a local, unauthenticated endpoint such
as Ollama — the ADR-0014 use case that previously needed server access to satisfy.

Model lists are operator-maintained and will go stale: providers rotate their line-ups faster
than this repository releases, and GWDG only publishes its current set through
`GET /v1/models`, which requires a key. Discovering models at runtime with the caller's key was
considered and deferred: it would make the model set provider-authoritative (acceptable — ADR-0014
already called the model pin "a scope decision", not a security one) but it cannot tell us
whether a model accepts `reasoning_effort`, which is what decision I depends on.

### E — The agent never spends the operator's key

`resolve_llm_config()` no longer falls back to `settings.llm_api_key`. Those three legacy
settings (`llm_api_key`, `llm_base_url`, `llm_chat_model`) now serve **only** docstring
enrichment, which sits behind `POST /enrich` and an access token. The `agent_enabled` property
is gone: there is no longer a state in which the server alone can run the agent.

Option F was rejected as an unnecessary setting. The Web IDE is served by the same backend as
the API, so browser and server are always in lockstep; a local operator who previously relied on
the server key now pastes it into the settings dialog once per browser. That is a real cost to
the "zero-config to start" promise, and it is accepted: it buys the removal of an anonymous
spending channel with no configuration for an operator to get wrong.

### I — Per-model reasoning-effort gating

Most vLLM-hosted open-weight models reject `reasoning_effort`, and inside a `StreamingResponse`
that failure surfaces as an opaque upstream 400 after the 200 headers are already flushed —
option G's failure mode is therefore especially poor. Option H is wrong for any provider that
mixes reasoning and non-reasoning models, which OpenAI does.

So each `LLMModelSpec` carries `reasoning_effort: bool`, published to clients as
`supports_reasoning_effort`. The parameter is passed as the OpenAI SDK's `omit` sentinel rather
than `None`, since `None` is a real value the SDK serialises. An effort chosen for a model that
does not support it is **dropped, not rejected** — a stale value in a user's `localStorage` must
not break a run after the operator edits the catalog.

### API surface

`GET /capabilities` now returns a typed `CapabilitiesResponse` instead of a loose dict:
`llm_providers` (the catalog, with per-model flags), `llm_default_provider` and
`llm_reasoning_efforts`. `agent_enabled`, `llm_base_url` and `llm_chat_model` are **removed** —
the first no longer exists, and publishing the latter two would misrepresent where an agent
request goes.

The Web IDE's settings dialog becomes provider → model → reasoning effort → API key, with the
effort control disabled for models that do not support it and the resolved `base_url` shown
read-only so the user can see where their key is sent. `AgentSettings` in `localStorage` gains
the three selection fields as optional, so an entry written before this change still loads.

### Consequences

* Good, because the agent endpoint cannot be aimed at a host the operator did not list, and the
  allowlist check is an id lookup rather than URL comparison — there is no normalisation bug to
  have.
* Good, because an anonymous caller can no longer spend the operator's LLM credits.
* Good, because users pick their provider and model without server access, and a local Ollama
  works through configuration the operator already controls.
* Good, because a bad selection fails as a 400 with an actionable message before the SSE stream
  starts, instead of as an upstream error mid-stream.
* Neutral, because operators must maintain model lists that will drift from what providers
  actually offer.
* Bad, because a local single-user deployment loses the zero-configuration agent: the key must
  now be entered in the browser even when it is already in the config file.

### Accepted residual risk

Rate limiting and request payload caps were considered and deliberately excluded from this
change. The following are therefore **known, accepted** properties of the endpoint, mitigated at
the deployment layer (reverse-proxy rate limits, or simply not exposing `/agent/stream`
publicly) rather than in application code:

* `/agent/stream` remains unauthenticated and unthrottled. One small request still fans out to
  up to `agent_max_iterations` (default 10) upstream calls plus catalog searches, so it is an
  amplifier against the operator's CPU and sockets even though the LLM spend is now the
  caller's.
* The backend acts as an **IP-anonymising relay** to allowlisted providers: a caller with their
  own OpenAI key can route it through the operator's address. It is constrained to the
  allowlisted hosts and to chat completions carrying the agent's own system prompt and tools,
  and the caller gains no capability they lack directly — but the operator's IP is the one the
  provider sees, and the operator's terms with that provider are the ones in play.
* `query`, `history`, `nodes`, `edges`, `session_id` and `user_id` are unbounded in size and
  charset. `user_id` in particular is caller-supplied and flows into Langfuse traces, so trace
  attribution is untrusted input.
* Allowlisted `base_url` values are served by the public `GET /capabilities`. Operators must not
  place a credential in a provider URL, and should treat any internal endpoint they add as
  disclosed.
* API keys still travel in the request body and therefore appear in access logs unless
  sanitised — unchanged from ADR-0014.

## Pros and Cons of the Options

### A — Caller sends the base URL, server validates against an allowlist

* Good, because it is the most literal reading of "these fields must pass a whitelist" and needs
  no id indirection.
* Good, because the request is self-describing: the URL in the body is the URL used.
* Bad, because the string comparison becomes security-critical, and equality after normalisation
  is genuinely hard (trailing slash, case, userinfo, IDN, percent-encoding, default ports).
* Bad, because a caller-supplied URL still reaches the HTTP client, so any gap in validation is
  an immediate SSRF.

### B — Opaque provider id (chosen)

* Good, because no caller string reaches the HTTP client; the bypass class disappears rather
  than being defended against.
* Good, because the catalog doubles as the UI's provider list, so `/capabilities` has something
  concrete to publish.
* Neutral, because clients must fetch `/capabilities` to learn valid ids.
* Bad, because a user cannot point the agent at an endpoint the operator has not listed, even
  their own local one.

### C — Keep the base URL pinned server-side

* Good, because it is the status quo and provably has no SSRF surface.
* Bad, because it does not meet the requirement: users cannot choose GWDG *or* OpenAI.

### D — Keep the server-key fallback

* Good, because a local deployment keeps a zero-configuration agent.
* Bad, because on a public deployment any anonymous caller spends the operator's credits, with
  no attribution and no cap beyond `agent_max_iterations`.

### E — Remove the server-key fallback (chosen)

* Good, because the anonymous spending channel is closed by construction, with no setting to
  misconfigure.
* Good, because it makes the split explicit: caller credentials for the agent, operator
  credentials for enrichment behind a token.
* Bad, because every user of every deployment must enter a key in the browser once.

### F — Remove it with an opt-in escape hatch

* Good, because it is secure by default while preserving the local zero-config path.
* Bad, because it adds a setting whose only job is to reintroduce the hazard, and a
  wrongly-enabled instance looks identical to a correct one from outside.

### G — Always forward the caller's reasoning effort

* Good, because no per-model configuration.
* Bad, because unsupported models fail as an opaque upstream 400 *after* the SSE 200 headers are
  flushed, which is the hardest failure mode to report well.

### H — One reasoning-effort flag per provider

* Good, because the configuration is a single boolean per entry.
* Bad, because OpenAI mixes reasoning and non-reasoning models, so the control would be offered
  for models that reject it.

### I — One flag per model (chosen)

* Good, because the UI can enable the control exactly where it applies, and the backend never
  forwards the parameter to a model that would reject it.
* Neutral, because model entries become tables; a bare string stays valid as shorthand for a
  model without reasoning-effort support.
