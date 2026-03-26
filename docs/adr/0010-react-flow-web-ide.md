---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: web-ide
---

# React Flow for the visual workflow editor

## Context and Problem Statement

The web IDE allows users to compose simulation workflows visually: nodes from the registry
are placed on a canvas, connected via typed ports, and the resulting graph is exported as
JSON. This requires an interactive graph editor with support for custom node renderers,
typed handles, and programmatic layout.

## Considered Options

* `@xyflow/react` (React Flow)

## Decision Outcome

Chosen option: **React Flow (`@xyflow/react`)**, because it is the most widely adopted
React graph editor library, provides first-class TypeScript support, has a rich API for
custom node and edge rendering, and integrates straightforwardly with the project's existing
React + Vite + Tailwind stack. The `dagre` layout library is used alongside React Flow for
automatic graph layout.

### Consequences

* Good, because custom node components (wrapping registry `NodeMetadata`) can be written as
  plain React components, keeping the rendering logic consistent with the rest of the UI.
* Good, because React Flow's built-in state management handles selection, dragging, and
  connection interactions without custom event plumbing.
* Neutral, because React Flow's open-source licence covers the use case here; the Pro
  features (advanced layout, collaboration) are not required.
