---
name: sim-atlas
description: Find and reuse existing simulation building blocks from the Simulation Atlas catalog when writing scientific, numerical or simulation Python — structure and file I/O, unit conversions, physics kernels, solvers, post-processing, or multi-step pipelines. Use when writing such code, when a needed routine may already exist in a research package, or when a physical quantity or unit has to line up between two calls.
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

## What the catalog will not do

It is read-only from here: there is no way to upload a workflow you wrote.
Publishing goes through `sim-atlas-toolkit` with an API token, which is the
user's decision, not yours.
