---
name: sim-atlas
description: Find and reuse existing simulation building blocks from the Simulation Atlas catalog when writing scientific, numerical or simulation Python — structure and file I/O, unit conversions, physics kernels, solvers, post-processing, or multi-step pipelines — and compose them as a plain Python script, a flowrep workflow, or an executorlib pipeline. Use when writing such code, when a needed routine may already exist in a research package, when a physical quantity or unit has to line up between two calls, or when asked to write, convert or publish a workflow or pipeline.
---

# Simulation Atlas

Simulation Atlas is a catalog of real, importable Python functions and
workflows contributed by research groups. Entries carry parameter datatypes,
physical units and quantities, so the catalog can answer questions the local
filesystem cannot — including functions in packages that are not installed here.

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

## Ask which format before writing code

As soon as the task needs **more than one catalog call chained together** — a
pipeline, a workflow, or just two calls where one feeds the other — stop and ask
the user which of three formats to write. Do not infer it from the task, and do
not default to one silently:

| Format | What it buys | What it costs |
|---|---|---|
| **pure Python** | nothing to learn, runs anywhere, easiest to read and debug | no recorded graph, not publishable, no scale-out |
| **flowrep** | a checked, serialisable DAG; the catalog's publishable format; inspectable before it runs | a restricted grammar — no arithmetic, no nested calls |
| **executorlib** | per-task cores/GPUs/runtime, SLURM and Flux, result caching | ordinary Python with no checks; wiring errors appear at run time |

Two things worth telling the user when you ask, because they change the answer:

- The choice is **not** permanent. A flowrep workflow can be executed by
  executorlib, and an executorlib pipeline can be exported and converted back to
  flowrep — see "Moving between formats" below.
- Pure Python written the way described below lifts into either framework later
  with little rework, so it is a reasonable starting point rather than a dead
  end.

If the user asks for one call and one call only, just write it. The question is
about composition, not about every line of scientific code.

## Every step comes from the catalog

This holds for all three formats. The format decides how steps are wired; it
never changes where they come from.

**Every step should be a function you found in the catalog.** Writing your own
is the exception and needs a reason you can state.

That is a reproducibility requirement, not a style preference. A catalog function
carries a recorded version, provenance, units and quantities, and someone else's
review; a pipeline built from catalog functions can be re-run and trusted by a
group that was not in this conversation. A step you write yourself is another copy
of a routine some research group already implemented — unreviewed, unmatchable
against the catalog, and a silent fork of the thing it duplicates.

So, per step of the pipeline:

1. `search_functions(...)` **before** writing that step — every step, not just
   the ones that look hard.
2. Chain with `find_by_signature(unit=..., match="parameter")`: "what accepts
   what the previous step produced", rather than assuming two functions fit.
3. `get_workflow_source(id)` on a nearby catalog workflow — the composition may
   already exist, in which case adapt it.
4. Only after two or three genuinely different searches come back empty may you
   write that step yourself.

Two things do justify a hand-written step: a thin wrapper around a compiled
callable, which neither flowrep nor executorlib can take directly (keep it to the
call, no science of your own inside it), and genuinely novel domain logic the
catalog lacks — write that one as if it will be published, with a real docstring
and units named in the parameter docs.

Glue that only rearranges data — renaming keys, zipping two lists, pulling a
field off an object — usually means the two steps were not the right pair. Search
once more for a function that takes what you actually have before writing an
adapter.

Then tell the user which steps came from the catalog (with their ids), which you
wrote, and what you searched for before writing each one. That is their cue to
publish the new function, or to point you at the package you missed.

## Writing it: pure Python

A plain script or module. No decorators, no executor — but write it so it can be
lifted into flowrep or executorlib later without being rewritten:

- Module-level named functions; call imported catalog functions directly.
- One call per assignment, left to right. No nested calls.
- No arithmetic between the steps. A unit conversion or a scaling factor is a
  function call, not an inline `* 1e-3` — that is the single habit that decides
  whether the script converts cleanly.
- Keep the pipeline in one function that takes its inputs as arguments and
  returns its result, with the script's I/O outside it.

Verify by running it. That is the whole advantage of this format.

## Writing it: flowrep

Read `references/flowrep.md` before writing the syntax. The body is a restricted
grammar, not ordinary Python: no arithmetic, no nested calls, one assignment per
node. Importing the module parses it and raises on any violation — always do
that, then print `.flowrep_recipe` to check the wiring.

## Writing it: executorlib

Read `references/executorlib.md` before writing the syntax. It is ordinary
Python, so nothing is checked at import time; the dependencies are the `Future`
objects you pass from one `submit` to the next.

Ask which executor to use before writing — `SingleNodeExecutor`,
`SlurmJobExecutor`, `SlurmClusterExecutor`, `FluxJobExecutor` or
`FluxClusterExecutor`. That depends on where the user runs the script and which
scheduler their site has, which is not something to detect or assume. Develop
against `SingleNodeExecutor` regardless, since it is the only one runnable here
and the interface is identical.

## Moving between formats

Both conversions go through python-workflow-definition, the interchange format
the catalog also stores. `references/executorlib.md` has the working code for
both; the reason to mention them to the user is that they dissolve the usual
trade-off:

- **flowrep → executorlib**: `fr.tools.flowrep2pwd(...)` then
  `python_workflow_definition.executorlib.load_workflow_json(file, exe)`. Write
  the checked, publishable recipe *and* run it on HPC resources. Requires a flat
  workflow and a default for every input.
- **executorlib → flowrep**: run with `export_workflow_filename=...`, then
  `fr.tools.pwd2flowrep(...)`. This is what keeps an executorlib pipeline from
  being a dead end for the catalog. It only works if the submitted functions are
  importable by module path, so import them rather than defining them in the
  driver script.

## What the catalog will not do

It is read-only from here: there is no way to upload a workflow you wrote.
Publishing goes through `sim-atlas-toolkit` with an API token, which is the
user's decision, not yours.
