---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: cross-cutting
---

# Store node metadata with links to external source repositories

## Context and Problem Statement

Simulation Atlas is a registry for reusable simulation building blocks. Each node has
associated metadata (name, type annotations, AI docstring, embedding) and a snapshot of
its source code (used for identity via SHA-256 and for AI enrichment). Beyond that, nodes
also have *runtime artifacts*: actual simulation inputs, outputs, result files, and datasets.
Two related questions arise:

1. Should SA store full source code history and act as a version control system?
2. Should SA store simulation runtime artifacts?

Both questions share the same answer: SA's role is *discoverability*, not storage or
versioning. A decision is needed to make this scope boundary explicit.

## Considered Options

* Store metadata in SA and link to an external source repository (e.g. GitHub, GitLab)
* Store only metadata and a source snapshot — no external link required or enforced
* Act as a version control system for node source code (store full history, branches, diffs)
* Store simulation runtime artifacts in SA (alongside metadata)

## Decision Outcome

Chosen option: **store metadata in SA and link to an external source repository**, because
the registry's core value is *discoverability* — helping researchers find and understand
existing building blocks. The authoritative copy of a node's source code must live in the
researcher's own VCS (GitHub, GitLab, or similar). Users are strongly encouraged to maintain
their source externally and provide a repository link when registering a node.

If a user uploads metadata without maintaining an external source repository, there is no
guarantee they will be able to reimport the function referenced by that metadata later. SA
does store an internal source snapshot at registration time, but this is an implementation
detail used solely for identity (SHA-256 hash, see ADR-0005) and AI enrichment — it is not
a user-facing retrieval guarantee.

SA does not store simulation runtime artifacts. Artifact storage belongs in a dedicated data
management platform.

A direct consequence of this scope decision is that Simulation Atlas is **nice-to-have
infrastructure**: if it goes down, no scientific work is blocked. Researchers lose QoL
features (search, AI enrichment), but all actual data and source code
remain in their own systems. This keeps availability and reliability requirements
proportional to the service's role.

### Consequences

* Good, because storage requirements remain small — metadata records are kilobytes, not
  gigabytes.
* Good, because there are no data-governance or access-control concerns around simulation
  data or source code — SA holds only a link and an internal snapshot.
* Good, because SA downtime has no impact on ongoing scientific work.
* Good, because the architecture stays simple: a single FastAPI process with in-memory
  (or MongoDB) storage suffices.
* Bad, because if a user registers a node without maintaining an external source repository,
  they cannot reliably reimport that function later — SA provides no guarantee of source
  retrieval.
* Neutral, because users who want source history, branching, or artifact provenance need
  their own VCS and data management platform — SA does not replace these.

## Pros and Cons of the Options

### Store only metadata and a source snapshot — no external link required

* Good, because the service stays lightweight and registration is simpler (no VCS link needed).
* Bad, because SA holds only one snapshot per node version with no link to the original
  source; if the internal snapshot is lost, the code is unrecoverable.
* Bad, because it implicitly encourages users to treat SA as their source of truth, which it
  is not designed to be.

### Act as a version control system for node source code

* Good, because SA would be the single place to track how a node's implementation evolved.
* Bad, because VCS is a solved problem (git); reimplementing it in SA would be a large
  engineering effort with no unique benefit.
* Bad, because researchers already have git repositories; pushing to SA as well creates
  redundancy and synchronisation burden.
* Bad, because SA downtime would block access to source history, raising availability
  requirements substantially.

### Store simulation runtime artifacts in SA

* Good, because the registry becomes a single source of truth for both discovery and data
  retrieval.
* Good, because artifact integrity can be verified (e.g. checksums on upload).
* Bad, because storage costs and operational complexity grow rapidly with artifact sizes
  (simulation outputs can be gigabytes to terabytes).
* Bad, because access control, retention policies, and data governance become SA's
  responsibility — a significant scope expansion.
* Bad, because SA downtime would directly block access to scientific data, raising
  availability requirements substantially.
