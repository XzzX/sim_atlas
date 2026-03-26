---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: cross-cutting
---

# Monorepo with four independent sub-packages

## Context and Problem Statement

Simulation Atlas consists of four distinct components: a backend API service, a search
frontend, a developer-facing ingestion toolkit, and a visual workflow editor. These
components share domain knowledge (e.g. the `NodeMetadata` schema via
`python-workflow-definition`) but have different runtimes, release cycles, and audiences.
A repository layout must be chosen that supports co-development without coupling deployments.

## Considered Options

* Single monorepo containing all four components as independent packages
* Separate repositories per component

## Decision Outcome

Chosen option: **monorepo**, because the components evolve together (schema changes in the
toolkit must be reflected in the backend immediately) and a single repository makes
cross-cutting refactors, shared CI, and ADRs much easier to manage.

Each sub-package (`backend/`, `frontend/`, `toolkit/`, `web_ide/`) has its own
`pyproject.toml` / `package.json` and can be installed, released, and tested independently.

### Consequences

* Good, because atomic commits can span a schema change in the toolkit and its corresponding
  backend handler.
* Good, because a single pull request covers cross-component features end-to-end.
* Neutral, because contributors working on only one component must clone the full repo; the
  sub-package structure makes it straightforward to ignore the rest.
