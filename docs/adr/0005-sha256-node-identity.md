---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: [backend, toolkit]
---

# SHA-256 source hash as node identity

## Context and Problem Statement

Each node registered in Simulation Atlas represents a specific version of a piece of
simulation code (a Python function or workflow). The system needs a stable, unique identifier
for nodes that: (a) detects when the same code is uploaded twice, (b) changes automatically
when the source code changes, and (c) does not require a centralised ID-issuing service.

## Considered Options

* SHA-256 hash of the node's source code
* UUID generated at upload time
* `(function_name, version)` composite key

## Decision Outcome

Chosen option: **SHA-256 hash of the node's source code**, because it makes identity
content-addressable: identical code always produces the same ID, making duplicate detection
free (a second upload of the same source returns HTTP 409 without any database lookup
beyond a key check), and any change to the source — however small — produces a new identity
without the developer having to manage version strings.

### Consequences

* Good, because duplicate uploads are detected trivially and cheaply.
* Good, because there is no external coordination needed to assign IDs.
* Good, because renaming a function without changing its body correctly reuses the existing
  node (the identity tracks the implementation, not the label).
* Bad, because two logically different functions that happen to have identical source code
  would collide.
* Neutral, because whitespace-only reformats produce a new identity; contributors should be
  aware of this.
