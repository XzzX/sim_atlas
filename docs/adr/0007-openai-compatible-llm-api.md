---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: backend
---

# OpenAI-compatible LLM API

## Context and Problem Statement

The backend uses an LLM for two tasks: generating semantic embeddings for nodes and powering AI-assisted search. It must be possible to run the system
against OpenAI's hosted API, a self-hosted model, or any other
provider that speaks the OpenAI wire protocol — without changing application code.

## Considered Options

* Use the OpenAI SDK with a configurable base URL and API key

## Decision Outcome

Chosen option: **OpenAI SDK with configurable base URL and API key**, because the OpenAI
wire protocol has become a de-facto standard and virtually all modern LLM serving stacks
(vLLM, Ollama, Together AI, etc.) implement it. The four environment variables
`LLM_API_URL`, `LLM_API_KEY`, `LLM_CHAT_MODEL`, and `LLM_EMBEDDING_MODEL` are sufficient
to point the backend at any compatible endpoint without touching application code.

The backend also strips `<think>…</think>` blocks from responses, accommodating
chain-of-thought reasoning models transparently.

### Consequences

* Good, because self-hosted models can be used for data-sovereignty reasons without any
  code change.
* Good, because switching providers (or running locally with Ollama for development) is a
  pure configuration change.
* Neutral, because the OpenAI SDK must be kept up to date as the wire protocol evolves.
