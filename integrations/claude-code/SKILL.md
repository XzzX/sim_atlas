---
name: sim-atlas
description: Find and reuse existing simulation building blocks from the Simulation Atlas catalog when writing scientific, numerical or simulation Python — structure and file I/O, unit conversions, physics kernels, solvers, post-processing, or multi-step pipelines — and compose them into flowrep workflows. Use when writing such code, when a needed routine may already exist in a research package, when a physical quantity or unit has to line up between two calls, or when asked to write, convert or publish a workflow or pipeline.
---

# Simulation Atlas

Simulation Atlas is a catalog of real, importable Python functions and
`@flowrep.workflow` pipelines contributed by research groups. Entries carry
parameter datatypes, physical units and quantities, so the catalog can answer
questions the local filesystem cannot — including functions in packages that are
not installed here.

Requires the `sim-atlas` MCP server (see the repository README). If its tools are
not available, skip this skill and write the code directly.

## When to use it

Search **before** hand-writing a non-trivial scientific routine. A curated,
unit-annotated function from a research package beats one re-derived from
memory.

Do **not** search for ordinary programming: string handling, plain file I/O,
plotting, dataframe wrangling, or anything the standard library and the usual
scientific stack already do well.

## The loop

1. `search_functions("<full sentence describing what the code should do>")`.
   Use domain terminology: *"compute the radial distribution function of an
   atomic structure"*, not *"rdf"*. The index is semantic and rewards detail.
2. Read the result block. It gives you the call signature, the exact import, an
   install hint and the catalog id — everything needed to write the call.
3. `get_function(id)` when you need the full docstring: argument meanings,
   units, defaults.
4. `find_by_signature(unit="K", match="parameter")` when chaining calls — "what
   accepts the value I just produced", or `match="return"` for "what produces
   what I need".
5. `get_workflow_source(id)` to read a complete pipeline as a worked example.
   Adapt it; do not guess at composition from individual signatures.

**Import what you find — never copy the body into the user's file.** The catalog
deliberately does not return function source for this reason.

If two or three searches turn up nothing relevant, stop searching and write the
code yourself. The catalog covers specific research domains, not everything.

## Before writing an import

Check that the module is actually importable here:

```python
import importlib.util
importlib.util.find_spec("<module from the import line>")
```

- **Importable** → write the call and run it. You have a real verification loop:
  import it, execute it, read the traceback, fix.
- **Not importable** → do not silently emit the import. Tell the user what the
  catalog found, which distribution provides it, and *propose* the install
  command. Wait for confirmation before installing anything.

Pick the command from the project's package manager, not a fixed default:

| Project contains | Use |
|---|---|
| `uv.lock` / `[tool.uv]` | `uv add <name>` |
| `pixi.toml` / `pixi.lock` | `pixi add <name>` |
| `environment.yml`, or an active conda env | `conda install -c <channel> <name>` |
| plain venv / `requirements.txt` | `pip install <name>` |

Match the ecosystem to the manager: use the catalog's `conda` entry for a conda
or pixi project and its `pypi` entry for pip or uv.

## Treat install hints as hints

The `# install:` line records what *an uploader's* environment contained. It is
best-effort metadata, not registry truth:

- No conda entry does **not** mean the package is unavailable on conda-forge.
- The recorded version is the one that was parsed, not a requirement.
- A catalog entry can be stale relative to the package's current source.

So propose, let the user confirm, and verify by importing rather than trusting
the metadata.

## Composing workflows

When the result is a multi-step pipeline — or the user asks for a workflow —
write it as a `@flowrep.workflow` function. That is the format this catalog
stores workflows in, so the pipeline stays inspectable, re-runnable and
publishable instead of being a one-off script.

Read `references/flowrep.md` before writing the syntax. The body is a restricted
grammar, not ordinary Python: no arithmetic, no nested calls, one assignment per
node. Importing the module parses it and raises on any violation — always do
that, then print `.flowrep_recipe` to check the wiring.

**Every node should be a function you found in the catalog.** Writing your own
`@flowrep.atomic` is the exception and needs a reason you can state.

That is a reproducibility requirement, not a style preference. A catalog function
carries a recorded version, provenance, units and quantities, and someone else's
review; a workflow built from catalog nodes can be re-run and trusted by a group
that was not in this conversation. A node you write yourself is another copy of a
routine some research group already implemented — unreviewed, unmatchable against
the catalog, and a silent fork of the thing it duplicates.

So, per step of the pipeline:

1. `search_functions(...)` **before** writing that step — every step, not just
   the ones that look hard.
2. Chain with `find_by_signature(unit=..., match="parameter")`: "what accepts
   what the previous node produced", rather than assuming two functions fit.
3. `get_workflow_source(id)` on a nearby catalog workflow — the composition may
   already exist, in which case adapt it.
4. Only after two or three genuinely different searches come back empty may you
   write that node yourself.

Two things do justify a hand-written node: a thin wrapper around a compiled
callable, which flowrep cannot turn into a node (keep it to the call, no science
of your own inside it), and genuinely novel domain logic the catalog lacks —
write that one as if it will be published, with a real docstring and units named
in the parameter docs.

Glue that only rearranges data — renaming keys, zipping two lists, pulling a
field off an object — usually means the two nodes were not the right pair. Search
once more for a node that takes what you actually have before writing an adapter.

Then tell the user which nodes came from the catalog (with their ids), which you
wrote, and what you searched for before writing each one. That is their cue to
publish the new node, or to point you at the package you missed.

## What the catalog will not do

It is read-only from here: there is no way to upload a workflow you wrote.
Publishing goes through `sim-atlas-toolkit` with an API token, which is the
user's decision, not yours.
