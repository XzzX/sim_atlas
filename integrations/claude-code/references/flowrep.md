# flowrep syntax reference

`flowrep` turns a plain Python function into a JSON-serializable recipe — a DAG
of nodes and edges that a workflow management system can run. It is the format
the Simulation Atlas stores workflows in.

This file is syntax only. For *which* functions may become nodes, see the
"Composing workflows" section of SKILL.md — the short version is that nodes come
from the catalog and writing your own is the exception.

Checked against **flowrep 0.6.2**. Upstream guide:
<https://github.com/pyiron/flowrep/blob/main/notebooks/user-guide.ipynb>

```python
import flowrep as fr
```

## Composition: a catalog function is already a node

A child call resolves in one of two ways: if the function carries
`.flowrep_recipe` it is used directly; otherwise flowrep reads its **source** and
parses it as an atomic node on the fly.

So an imported catalog function needs no decoration and no wrapper — import it
and call it:

```python
from some_research_pkg.analysis import rescale, total   # from search_functions

@fr.workflow
def summarize(values, factor):
    """Rescale a list of values and total them."""
    rescaled = rescale(values, factor)
    out = total(rescaled)
    return out
```

`@fr.workflow` attaches `.flowrep_recipe` and takes the docstring as the recipe's
`description`. The function stays an ordinary callable: `summarize([1.0], 3.0)`
still runs normally.

## The workflow body is a restricted grammar

The decorator parses the function's AST **at decoration time**, so an invalid body
raises as soon as the module is imported. Every statement must be one of:

- `name = some_call(...)`
- `lo, hi = some_call(...)` — unpacking a multi-output node
- `alias = other_symbol`, or attribute/item access on a known symbol
  (`s.positions`, `d["energy"]`)
- a single final `return` of bare symbols

These **fail to parse**:

| Rejected | Instead |
|---|---|
| `out = s * 2` — any arithmetic | call a node that does the arithmetic |
| `out = scale(add(x, y))` — nested calls | assign the inner call to a name first |
| `return add(x, y)` | `out = add(x, y)` then `return out` |
| no return statement | always return something |
| `if flag:` with a plain test | the test must itself be a function call |
| `for _ in range(3):` | loops must iterate a symbol *and* carry an accumulator |

The arithmetic ban has a consequence worth noticing: you cannot quietly do the
physics in the body. A unit conversion or a scaling factor has to be a node.

Literal arguments are fine (`scale(x, 3.0)`, strings, lists) — each becomes its
own `constant_0` node. Keyword arguments and parameter defaults are fine. Local
`import` statements inside the body are ignored, not rejected.

Treat `if`/`for` as advanced. Write a straight-line DAG unless asked otherwise.

## What cannot be a node

Because flowrep parses a child's **source**, these raise
`SourceCodeUnavailableError` ("source code unavailable"):

- compiled code — `np.add`, `math.hypot`, builtins, C extensions
- lambdas and dynamically defined functions

A compiled callable needs a thin `@fr.atomic` wrapper — the call and nothing else:

```python
@fr.atomic("total")
def total(values):
    """Sum values — wraps a compiled numpy call so it can be a node."""
    result = float(np.sum(values))
    return result
```

Alternatively `fr.schemas.AtomicRecipe(...)` builds a recipe around an existing
function without a wrapper, which also handles variadic signatures — it can expose
a safe subset of `np.linspace`'s parameters, or force arguments keyword-only.

Separately: everything decorated with `@fr.atomic` or `@fr.workflow` must live at
**module level**. A function defined inside another function cannot be resolved by
qualname and fails with `Could not find attribute '<name>' of <name>`.

## Output port names

Ports are named by the first rule that applies:

1. explicit decorator labels — `@fr.atomic("quotient", "remainder")`
2. `Annotated[float, {"label": "magnitude"}]` in the return annotation
3. the variable name in the return statement — `return result` gives `result`
4. otherwise `output_0`, `output_1`, …

A catalog function ending in `return a + b` therefore contributes a port called
`output_0`. That is the catalog's function, not yours to rename. In a node you
write yourself, name the returned value.

A single label collapses a tuple return into one port:
`@fr.atomic("tuple_return")` on `return (x, z, y)` gives one port, not three.

Labels must be valid Python identifiers, must not be keywords, and must not be
`inputs` or `outputs`.

## Nesting

Workflows nest arbitrarily. A `@fr.workflow` called inside another becomes a
single encapsulated child node — the parent sees only its ports, never its
internals. An inner function must be decorated with `@fr.workflow` to nest;
undecorated, it collapses into one opaque atomic node.

A catalog workflow found with `search_functions(kind="workflow")` nests the same
way: import it and call it rather than flattening its steps into your body.

## Verifying

Importing the module is the check — decoration parses the AST and raises on any
grammar violation. Then read the recipe back to confirm the wiring:

```python
recipe = summarize.flowrep_recipe
print(recipe.inputs, recipe.outputs)
print(list(recipe.nodes))     # e.g. ['rescale_0', 'total_0']
print(recipe.edges)           # node output -> node input
```

A missing step, or an unexpected `constant_0`, means a value was wired as a
literal instead of flowing from a node.

Executing is optional — only when the inputs are cheap and already available.
Never fabricate a structure file or launch a solver just to prove a graph parses:

```python
dag = fr.tools.run_recipe(summarize.flowrep_recipe, values=[1.0, 2.0], factor=3.0)
print({k: v.value for k, v in dag.output_ports.items()})
```

## Also available

- `fr.parse_atomic(fn)` — a recipe without decorating the function.
- `@fr.dataclass` — a dataclass becomes a node with one `instance` output, and
  gains `.flowrep_recipe_unpacking` for the reverse direction.
- `recipe.draw(depth=1)` — render the graph as SVG.
