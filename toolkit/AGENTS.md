# toolkit

Client-side library for parsing installed Python packages and uploading simulation node metadata to the backend.

## Commands

```bash
uv run pytest                           # run tests
uv run coverage run -m pytest           # run tests with coverage
uv run ruff check .                     # lint
uv run ruff format --check .            # check formatting
uv run pyright                          # type-check (strict mode)
```

## Key Patterns

- **Entry point**: `cli.py` → `orchestrator.py` (`upload_modules`) orchestrates the full pipeline: module import → recursive traversal (`collector.py`) → per-object parsing (`uploader.py` → `parsers/parser.py`) → storage via a `NodeStore` (`node_store.py`; `http_node_store.py` is the only implementation today); a store is an async context manager whose `aclose` releases event-loop-bound resources (e.g. connections) while leaving the store usable — `_upload_modules_async` closes only a store it built itself, and the sync `upload_modules` additionally releases a passed-in store before its `asyncio.run` loop ends
- **Parser plugins**: add new parsers in `parsers/` following the existing modules (`aiflow.py`, `flowrep_parser.py`, `python_function.py`, `python_workflow_definition.py`) and register them in `parsers/__init__.py`; each parser receives a `ParseContext` (`settings` + `store`, see `context.py`) and a single Python object, returns `[]` to defer, and stores through `ctx.store`, returning `list[NodeResult]` (a `NodeStatus` of `CREATED`/`EXISTS` plus the stored `NodeResponse`); `parsers/metadata.py` holds the shared annotation and docstring utilities
- **Two-phase parsers (ADR-0025)**: the successor contract, coexisting with the legacy `parse` functions until the cutover (#227). A parser class in `plugin.py`'s `Parser` shape sits beside each module's legacy `parse`; its `identify` (cheap: at most one node id — `None` for a container — plus children) and `describe` (that node's draft) stay synchronous and pure, while `pipeline.py` (`run_pipeline`) owns all I/O — existence checks, enrichment, self-containment, validation and storing
- **Core parsing**: `parsers/parser.py` (`get_metadata`) tries each registered parser in order and returns the first non-empty result; module-level traversal and recursion strategies (`no`, `import`, `filesystem`) live in `collector.py`
- **Schema**: the wire models (`NodeRequest`, `NodeResponse`, `Annotation`, `Reference`, `WfDefinition`, …) come from `sim_atlas_models` (the `models/` package, ADR-0024), pinned exactly and released in lockstep; never redefine them here. Request models are `extra="forbid"`: parsers build nodes with `NodeRequest.model_construct(...)` (no validation), and `HttpNodeStore.create_node` re-validates before sending, so a response-side value inside a request (e.g. an `AnnotationResponse` copied from a stored node) is rejected there — convert it explicitly, as `parsers/aiflow.py` `to_wf_definition` does
- **Provenance**: `provenance.py` resolves which distribution an object came from (`apply_provenance(metadata, obj.__module__)`), populating `packages` (pypi + conda, via `importlib.metadata` and `conda-meta/*.json`) plus author/URL/dependency metadata; call it from every parser that knows its module of origin. It is best-effort and never raises (ADR-0012, ADR-0019)
- **CLI**: `cli.py` provides the `sim-atlas-upload` entry point as `UploadCommand`, a `ToolkitSettings` subclass run via pydantic-settings' `CliApp`; flags are derived from field names (kebab-case) and every option also reads its `SIM_ATLAS_*` env var — add a field, not an argument parser
- **No server code**: this package runs entirely on the client machine; never add server-side dependencies

## Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## Code Quality — Write It Right First Time

**Run `uv run ruff check . && uv run ruff format --check . && uv run pyright` before declaring done. Fix all errors before moving on.**

### Type safety (Pyright strict)
- Annotate every function parameter and return type — no implicit `Any`.
- Use `X | Y` union syntax (Python 3.10+), never `Optional[X]` or `Union[X, Y]`.
- Prefer `X | None` over wrapping in `Optional`.
- Use `list[X]`, `dict[K, V]`, `tuple[X, ...]` (lowercase), not `List`, `Dict`, `Tuple` from `typing`.
- Only import from `typing` what has no builtin equivalent: `TypeVar`, `Protocol`, `TypedDict`, `Literal`, `overload`, `cast`, `TYPE_CHECKING`.
- Narrow types explicitly with `isinstance` checks or `assert` before use; don't cast blindly.
- Never use `# type: ignore` without a specific error code and a comment explaining why.

### Ruff lint rules enforced (see pyproject.toml)
- **UP**: use modern Python syntax — `X | Y`, `type` aliases, `match` where appropriate.
- **I**: imports are sorted — stdlib → third-party → local, one blank line between groups.
- **F**: no unused imports or variables; remove them (don't comment them out).
- **B**: no mutable default arguments, no `assert` in production logic.
- **SIM**: simplify boolean returns, `if`/`else` chains, and `with` blocks.
- **C4**: prefer comprehensions over `map`/`filter`; avoid unnecessary `list()` wrapping.
- **ERA**: no commented-out code.
- **PL**: Pylint rules — avoid too-many-branches, too-many-return-statements, etc.

### Formatting (ruff format)
- 88-character line limit (E501 is ignored so long lines won't error, but keep them readable).
- Use double quotes for strings.
- Trailing commas in multi-line collections.

## Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.
