---
status: accepted
date: 2026-04-27
deciders: Sebastian Eibl
scope: [backend, web-ide]
---

# Multi-turn agent conversation via client-carried history

## Context and Problem Statement

The workflow-builder agent currently processes each user message as a completely independent
request: the backend builds a fresh message list from the system prompt and the single
incoming query, runs the tool loop, and closes the connection. This means the agent has no
memory of previous turns — it cannot refer back to earlier questions, earlier search
results, or a clarification it previously asked the user.

To support interactive dialogue (the agent asking clarifying questions, the user refining a
request over several turns, or the agent acknowledging earlier context), the agent needs
access to the conversation history from prior turns.

The solution must also work correctly when multiple users use the frontend simultaneously
and when the backend is scaled horizontally across several worker processes.

## Considered Options

* **A — Context-enriched follow-up query**: no history field; instead the frontend
  auto-composes the next user message so that it embeds the relevant prior context inline
  (e.g. "Build a MD simulation. [Clarification: Which temperature unit? → Kelvin]").
* **B — Client-carried history in `AgentRequest`**: add a `history` field to `AgentRequest`
  containing the ordered list of prior `{role, content}` turns; the browser accumulates this
  list and sends it with every request; the backend injects it between the system prompt and
  the current query before calling the LLM.
* **C — Server-side session state with suspend/resume**: the backend stores the in-progress
  `messages` list in memory keyed by a session ID; when the agent asks a clarification
  question the generator is paused; a separate `POST /agent/resume/{session_id}` endpoint
  injects the user's answer and resumes the loop.

## Decision Outcome

Chosen option: **B — Client-carried history in `AgentRequest`**, because it keeps the
backend fully stateless, works transparently under multi-user and multi-process deployments,
and requires only a small extension to the existing request model and frontend state.

The `AgentRequest` model gains one optional field:

```python
class AgentRequest(BaseModel):
    query: str
    nodes: list[GraphNodeContext]
    edges: list[GraphEdgeContext]
    history: list[dict[str, str]] = []  # [{"role": "user"|"assistant", "content": "..."}]
    # (llm_api_key, llm_api_url, llm_chat_model from ADR-0014 omitted for brevity)
```

The runner inserts `history` entries as `ChatCompletionMessageParam` items after the system
prompt and before the current user query, giving the LLM the full conversation context.

The frontend accumulates history across turns: after each completed `done` event it appends
the user query and the assistant's final `message` content to a local `history` array that
is included in every subsequent `AgentRequest`.

The special case where the agent wants to ask a clarifying question is handled by a new
`ask_clarification` tool: calling it causes the backend to emit a `clarification` SSE event
(carrying the question text and an optional list of suggested answers), emit `done` with
the current graph state, and exit the loop. The frontend renders the question as a card
with clickable option buttons; the selected answer is sent as the next user message with the
accumulated history, allowing the agent to continue naturally.

### Consequences

* Good, because the backend remains a pure function of the request — no session store,
  no shared mutable state, no process-affinity requirement. Multiple users and multiple
  worker processes work without coordination.
* Good, because the approach composes cleanly with the client-supplied LLM credentials
  decision (ADR-0014): both the credentials and the history travel in the request body and
  are discarded afterwards.
* Good, because history is opt-in and backward-compatible: existing callers that omit the
  field get exactly the current single-turn behaviour.
* Neutral, because the accumulated history grows the LLM context window across turns. For
  typical interactive sessions (5–15 turns) the overhead is small relative to the system
  prompt; very long sessions may eventually hit the model's context limit, at which point
  older turns can be pruned or summarised on the client side.
* Bad, because the client is responsible for maintaining the history correctly; a
  page refresh or navigation away discards the history. This is acceptable for the current
  use case where the agent is embedded in a single-page application.

## Rejected Options

**Option A** avoids history entirely but makes the composed query unnatural and brittle: the
agent cannot reason about what it previously searched or proposed, and the inline encoding of
prior context is a hand-crafted approximation of what a proper message list provides. It also
shifts complexity into the frontend (composing the context string) without eliminating it.

**Option C** is the most powerful approach — the agent loop truly pauses mid-iteration — but
it introduces server-side mutable state that breaks horizontal scaling. Each in-flight
session holds a suspended Python coroutine and an open SSE connection in the process that
owns it. A resume request landing on a different worker process has no access to that
coroutine. Making it work across processes requires externalising the session state (e.g. to
Redis), adding TTL-based cleanup, and coordinating connection affinity — a significant
infrastructure cost for a feature that Option B covers adequately without any of it.
