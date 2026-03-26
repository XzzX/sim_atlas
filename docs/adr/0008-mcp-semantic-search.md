---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: backend
---

# Expose semantic search as an MCP tool

## Context and Problem Statement

Simulation Atlas aims to be accessible not only to human users through its web frontend but
also to AI agents and LLM-powered tools. The Model Context Protocol (MCP) is emerging as a
standard for exposing capabilities to LLM agents (including GitHub Copilot and Claude).
Making the node registry queryable from agents would extend its reach significantly without
building a separate integration.

## Considered Options

* Mount an MCP server directly onto the FastAPI app using `fastapi-mcp`

## Decision Outcome

Chosen option: **mount MCP server onto the FastAPI app via `fastapi-mcp`**, because it
exposes existing FastAPI routes (specifically `GET /api/v1/semantic_search`) as MCP tools
with zero duplication. The MCP server is co-deployed with the API — no additional process,
port, or infrastructure is required. Agents connect to the same URL as the web frontend.

### Consequences

* Good, because the semantic search capability is available to LLM agents (Copilot, Claude,
  etc.) without a separate deployment.
* Good, because the MCP tool definition is derived automatically from the FastAPI route's
  Pydantic schema and OpenAPI description.
* Neutral, because `fastapi-mcp` is a relatively new library; its API may change.
