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

- **Entry point**: `node_store.py` (`NodeStore`) orchestrates the full pipeline: module import → recursive traversal → per-object parsing → HTTP upload
- **Parser plugins**: add new parsers in `parsers/` following the existing modules (`dataclass_node.py`, `pyiron_core.py`, `pyiron_workflow.py`, `python_function.py`, `python_workflow_definition.py`); each parser receives a single Python object and returns `list[Metadata]`; `parsers/metadata.py` holds the shared `Metadata` model and annotation utilities used by all parsers
- **Core parsing**: `parser.py` (`get_metadata`) tries each registered parser in order and returns the first non-empty result; module-level traversal and recursion strategies (`no`, `import`, `filesystem`) live in `NodeStore.upload_module`
- **Schema**: two distinct types — `Metadata` (`parsers/metadata.py`, internal parser output) and `NodeRequest` (`models.py`, HTTP upload payload sent to the backend); keep both in sync with the backend's Pydantic schemas
- **CLI**: `cli.py` provides the `sim-atlas-upload` entry point; reads `SIM_ATLAS_API_URL` and `SIM_ATLAS_API_TOKEN` env vars as defaults
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
