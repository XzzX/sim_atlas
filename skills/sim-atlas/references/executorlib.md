# executorlib reference

`executorlib` extends the standard `concurrent.futures.Executor` interface so
that individual Python function calls can be distributed across HPC resources,
with cores, GPUs and runtime assigned **per call**.

It is an *execution layer*, not a file format. The pipeline is ordinary Python:
the DAG is implicit in which `Future` you pass where. Nothing is parsed, so
nothing is rejected at write time — the price of that freedom is that a wrong
wiring shows up at run time, not at import time.

This file is syntax only. For *which* functions may become tasks, see the
"Every step comes from the catalog" section of SKILL.md — the short version is
that tasks come from the catalog and writing your own is the exception.

Checked against **executorlib 1.10.3**. Upstream guide:
<https://executorlib.readthedocs.io/en/latest/README.html>

## Choosing the executor

Five classes, same interface. The right one depends on where the script runs,
which is a fact about the user's machine — **ask, do not guess**:

| Class | Run it from | Use when |
|---|---|---|
| `SingleNodeExecutor` | laptop, workstation, one node | development, testing, anything not on a scheduler |
| `SlurmJobExecutor` | inside an `salloc`/`sbatch` allocation | many tasks within resources you already hold |
| `SlurmClusterExecutor` | a SLURM login node | each task becomes its own `sbatch` job |
| `FluxJobExecutor` | inside a Flux allocation | high-throughput short tasks |
| `FluxClusterExecutor` | a Flux login node | long tasks, survives disconnects |

Write `SingleNodeExecutor` while developing even when the target is a cluster:
it is the only one you can actually run here, and switching is a one-line
change because the interface is identical.

The `*ClusterExecutor` classes need `pysqa` and a configured scheduler; the Flux
classes need a Flux installation. Neither will work on a plain machine.

## submit, and the implicit DAG

```python
from executorlib import SingleNodeExecutor
from some_research_pkg.analysis import rescale, total   # from search_functions

with SingleNodeExecutor() as exe:
    scaled = exe.submit(rescale, values, 3.0)
    summed = exe.submit(total, scaled)       # Future in -> dependency
    print(summed.result())
```

Passing a `Future` as an argument is the whole dependency mechanism: executorlib
resolves it before the task runs, so `scaled` never has to be `.result()`-ed by
hand. Calling `.result()` mid-pipeline blocks and serialises the graph — do it
once, at the end.

The `with` block matters. On exit the executor waits for outstanding tasks and
shuts its workers down; without it, workers leak.

## map

```python
with SingleNodeExecutor() as exe:
    results = list(exe.map(rescale, values_list, factor_list))
```

`map` is the parallel-over-inputs case. It returns results, not futures, so it
cannot feed another task lazily — use a list comprehension over `submit` when
the outputs are inputs to a later step:

```python
    futures = [exe.submit(rescale, v, 3.0) for v in values_list]
    combined = exe.submit(total, futures)     # a list of futures is resolved too
```

## Multiple outputs, and reaching into a result

A `Future` is opaque; you cannot unpack or subscript it directly. Two helpers
keep the laziness:

```python
from executorlib import split_future, get_item_from_future

with SingleNodeExecutor() as exe:
    pair = exe.submit(min_and_max, values)        # returns a 2-tuple
    lo, hi = split_future(pair, 2)                # two futures, nothing blocks
    span = exe.submit(difference, hi, lo)

    result = exe.submit(analyse, structure)       # returns a dict
    energy = get_item_from_future(result, "energy")
    report = exe.submit(format_energy, energy)
```

`split_future(fut, n)` needs the length up front. `get_item_from_future(fut, key)`
takes a dict key. Both return lazy selectors that you pass to another `submit` —
printing one shows a pending object, not a value.

## Resources

```python
with SingleNodeExecutor() as exe:
    fs = exe.submit(run_solver, structure, resource_dict={"cores": 4})
```

`resource_dict` keys: `cores`, `threads_per_core`, `gpus_per_core`, `num_nodes`,
`exclusive`, `cwd`, `run_time_max` (seconds), `priority`, `error_log_file`,
`cache_key`, `cache_directory`, `slurm_cmd_args`.

Set it per `submit` when tasks differ, or once on the executor as a default. An
MPI-parallel task must import `mpi4py` **inside** the function — the import has
to happen in the worker process, not the submitting one:

```python
def calc(i):
    from mpi4py import MPI
    return i, MPI.COMM_WORLD.Get_size(), MPI.COMM_WORLD.Get_rank()
```

`block_allocation=True` reserves workers once and reuses them, which is much
faster for many same-shaped tasks — but then the resources belong to the
executor, so declare them there rather than per `submit`.

## Caching

```python
with SingleNodeExecutor(cache_directory="./cache") as exe:
    ...
```

Results are keyed by function and arguments and stored as HDF5. Re-running the
script returns cached results instead of recomputing — the reason to reach for
this is an expensive step you are iterating around, not correctness.

`get_cache_data("./cache")` returns one dict per task with `function`,
`input_args`, `input_kwargs`, `output`, `resource_dict` and `runtime`. That is a
real audit trail: use it to check what actually ran.

The `*ClusterExecutor` classes cache by default (`executorlib_cache`), which is
what lets them reconnect to jobs that outlive the submitting process.

## What can be submitted

executorlib pickles the callable with `cloudpickle`, so plain functions, nested
functions and lambdas all work — but it also has to bind arguments to parameter
names, and some C-level callables defeat that:

| Callable | Result |
|---|---|
| a named module-level function | works — do this |
| builtins (`sum`, `len`) | works |
| numpy ufuncs (`np.add`) | works |
| `np.sum`, `np.mean`, `np.linalg.norm` | `TypeError: unsupported callable` |
| `math.hypot` and similar C functions | `TypeError: no signature found` |

So the rule matches the catalog's anyway: submit named functions imported from
real modules. If you need a compiled routine, wrap it in a named function and
submit the wrapper.

On a cluster the function must also be **importable in the worker's
environment**. A function defined in the driver script pickles fine for
`SingleNodeExecutor` but is a common cause of failures once tasks become
separate jobs.

## Inspecting the graph without running it

```python
with SingleNodeExecutor(export_workflow_filename="workflow.json") as exe:
    scaled = exe.submit(rescale, values, 3.0)
    summed = exe.submit(total, scaled)
```

This writes the dependency graph as **python-workflow-definition** JSON — the
same format the catalog understands. Three things to know:

- **Nothing executes.** `summed.result()` is `None` in export mode. This is an
  inspection and publishing path, not a dry run you can also get answers from.
- Function nodes are recorded as `module.name`, so functions defined in the
  driver script come out as `__main__.rescale` and are useless to anyone else.
  Import them from a module.
- `resource_dict` is **not** captured. The export is the graph, not the
  resource plan.

`plot_dependency_graph=True` exists but needs IPython and a notebook; prefer the
JSON export in a terminal.

## Verifying

There is no decoration-time check, so verification is running it:

1. Run the pipeline with `SingleNodeExecutor` on cheap inputs — small arrays,
   a tiny structure. Never fabricate a structure file or launch a real solver
   just to prove the wiring.
2. If the inputs are not cheap, export the graph instead and read the JSON:
   every `submit` should appear as a function node, and each dependency as an
   edge. A step that shows up with a literal `input` node where you expected an
   edge means a `Future` was resolved too early.
3. Exceptions surface at `.result()`, not at `submit`. A pipeline that "runs"
   without ever calling `.result()` has verified nothing.

## Moving to and from flowrep

Both directions go through python-workflow-definition, and both are worth
knowing because they remove the need to choose once and for all.

**Run a flowrep workflow on HPC.** flowrep gives the checked grammar and the
publishable recipe; executorlib gives the resources:

```python
import flowrep as fr
from executorlib import SingleNodeExecutor
from python_workflow_definition.executorlib import load_workflow_json

pwd = fr.tools.flowrep2pwd(pipeline.flowrep_recipe, a=1, b=2, factor=3.0)
with open("pipeline.json", "w") as f:
    f.write(pwd.model_dump_json(indent=2))

with SingleNodeExecutor() as exe:
    print(load_workflow_json("pipeline.json", exe).result())
```

`flowrep2pwd` needs a default for **every** workflow input, and the workflow
must be flat — atomic children only, one output port each. Nested `@fr.workflow`
children have to be inlined first.

**Publish an executorlib pipeline.** Export it, then convert:

```python
import json
import flowrep as fr
from python_workflow_definition.models import PythonWorkflowDefinitionWorkflow

with open("workflow.json") as f:
    wf = PythonWorkflowDefinitionWorkflow(**json.load(f))
recipe, defaults = fr.tools.pwd2flowrep(wf)
```

This only works if the exported nodes are real importable functions — see the
`__main__` warning above. Publishing itself still goes through
`sim-atlas-toolkit`, which is the user's call.
