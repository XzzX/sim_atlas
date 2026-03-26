---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: cross-cutting
---

# Use MADR as Architecture Decision Records format

## Context and Problem Statement

The project needs a lightweight, consistent way to record architectural decisions so that
future contributors can understand why things are the way they are — not just what they are.
The format should be easy to write, easy to read in a text editor or on GitHub, and ideally
machine-parseable for tooling.

## Considered Options

* MADR (Markdown Any Decision Records) — structured Markdown with YAML frontmatter

## Decision Outcome

Chosen option: **MADR**, because it strikes the best balance between structure and brevity.
The YAML frontmatter makes status and metadata queryable, the Markdown body is readable
without tooling, and the format is well-documented with an active community.

### Consequences

* Good, because frontmatter fields (`status`, `date`, `deciders`, `scope`) can be parsed
  programmatically to generate index pages or dashboards.
* Good, because the format enforces consistently listing considered options, preventing
  decisions from looking like foregone conclusions.
* Neutral, because contributors need to learn the template once; the README provides guidance.
