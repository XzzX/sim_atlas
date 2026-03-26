---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: cross-cutting
---

# Information is provided on a best-effort basis without freshness or correctness guarantees

## Context and Problem Statement

When a node is registered in Simulation Atlas, a snapshot of its metadata and source code is
captured at that point in time. The authoritative source lives in an external repository
(see ADR-0011). SA does not monitor upstream repositories for changes; if a researcher
updates, deprecates, or removes a function after registration, SA is not notified and its
stored record silently becomes stale.

The question is: should SA implement a mechanism to detect and reflect upstream changes, or
should it explicitly accept and document a best-effort quality policy?

## Considered Options

* Implement upstream synchronization (polling or webhook-based)
* Provide no freshness guarantee and document a best-effort policy

## Decision Outcome

Chosen option: **no freshness guarantee / best-effort policy**, because SA's role is
*discoverability*, not source-of-truth storage or change tracking (see ADR-0011). Any
synchronization mechanism would require researchers to maintain valid repository links,
handle authentication to private repositories, deal with renamed or deleted resources, and
add significant operational complexity — all disproportionate to SA's role as a
convenience tool.

Instead, SA explicitly communicates to users that:

1. Information is provided on a best-effort basis.
2. Neither correctness nor up-to-dateness is guaranteed.
3. Upstream source code may have changed after registration without SA being aware of it.
4. Users who need authoritative information must consult the upstream repository directly.

This policy should be surfaced in the UI (e.g. a persistent disclaimer) and in API
documentation, so users are never misled into treating SA records as canonical.

### Consequences

* Good, because no synchronization infrastructure is needed — SA stays operationally simple.
* Good, because the policy is honest and sets correct user expectations upfront.
* Good, because the decision is consistent with ADR-0011 (SA is a discovery tool, not a VCS
  or authoritative registry).
* Bad, because stale records can mislead users who do not notice the disclaimer.
* Neutral, because users who need live, authoritative metadata must check the upstream
  repository — SA is a starting point, not a final answer.

## Pros and Cons of the Options

### Implement upstream synchronization (polling or webhook-based)

* Good, because records would stay closer to their upstream state over time.
* Bad, because requires SA to store and validate repository URLs and credentials for every
  registered node.
* Bad, because handling deleted, renamed, or moved resources is complex and error-prone.
* Bad, because polling at meaningful frequency is resource-intensive; webhooks require
  researchers to configure them in their own repositories.
* Bad, because private repositories are inaccessible to SA without per-user auth tokens,
  creating a security and data-governance concern.
* Bad, because significant added complexity is disproportionate to SA's role as a
  convenience / nice-to-have tool.

### No freshness guarantee / best-effort policy (chosen)

* Good, because SA requires no access to external repositories after registration.
* Good, because the service stays simple and low-maintenance.
* Good, because the policy is transparent — users know they are seeing a registration-time
  snapshot.
* Bad, because records may become silently stale without any automatic warning to users.
