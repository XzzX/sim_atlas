---
status: accepted
date: 2026-04-02
deciders: Sebastian Eibl
scope: cross-cutting
---

# JupyterHub-like scale-agnostic server-client infrastructure

## Context and Problem Statement

Sim Atlas needs a deployment model that supports the full range of use cases researchers
actually encounter:

- A **single researcher** who wants a personal searchable catalogue with zero coordination
  overhead.
- A **research group or HPC centre** that wants a shared, curated catalogue for all members.
- A **community or project** that wants a public, internet-facing instance anyone can query.

The three goals driving the choice are:
1. **Shareability** — a running instance must be discoverable and queryable by multiple users.
2. **Quality control** — different operators should be able to enforce their own content
   policies (e.g., a curated group instance vs. an open community instance).
3. **Simplicity** — any individual researcher must be able to install and run the full stack
   on their own laptop, without coordinating with an admin.

An additional hard constraint is **a single shared codebase**: the same `sim-atlas-backend`
package must serve all of the above scenarios without per-deployment forks.

## Considered Options

* **Scale-agnostic self-hosted server** — the same backend package runs everywhere,
   from `localhost` on a personal PC to a globally reachable production server; the deployment
   scope is determined entirely by the operator's network and configuration.

## Decision Outcome

Chosen option: **scale-agnostic self-hosted server**, because it satisfies all three goals
with a single codebase and zero additional complexity per deployment tier.

In every case the running software is identical. The only difference is the network
configuration and the JWT signing secret chosen by the operator. Because different instances
are independent, each can enforce its own quality control policies (e.g., restricted write
access, manual curation, content moderation) without affecting other instances.

### Consequences

* Good, because `pip install sim-atlas-backend && uvicorn sim_atlas_backend.main:app` is all
  that is needed for a personal instance — no system admin required.
* Good, because data sovereignty is preserved: each instance owns its own data and is never
  forced to synchronise with any other instance.
* Good, because quality control is a per-instance concern: operators configure authentication,
  write permissions, and moderation independently.
* Good, because a single codebase means bug fixes and new features are available to all
  deployment scales simultaneously.
* Good, in the future, the frontend can be enabled to query multiple servers to achieve federation.
* Neutral, because the toolkit client must be pointed at a specific instance URL; this is a
  one-time configuration step.
* Neutral, data needs to be uploaded to every instance separately.

## Pros and Cons of the Options

### Scale-agnostic self-hosted server (chosen)

* Pro: users are used to JupyterHub which shares a similar architecture
* Pro: single codebase covers the full deployment spectrum
* Pro: personal install is a one-liner; no coordination required
* Pro: each instance can have independent quality control and access policies
* Pro: data stays within the operator's network by default
* Pro: no mandatory dependency on any third-party service
* Con: cross-instance discovery requires manual configuration or an out-of-scope registry

