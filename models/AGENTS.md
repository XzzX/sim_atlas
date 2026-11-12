# models

`sim-atlas-models` (`sim_atlas_models`): the Pydantic wire schema of the REST API, shared by `backend` and `toolkit` (ADR-0024). Pure data definitions; the only runtime dependency is `pydantic`.

## Commands

```bash
uv run pytest                           # run tests
uv run ruff check .                     # lint
uv run ruff format --check .            # check formatting
uv run pyright                          # type-check (strict mode)
```

## Key Patterns

- **Field ownership is enforced by types**: request models (`NodeRequest`, `Annotation`, `Reference`, `ExecutionResultRequest`, and the client-owned `Wf*`, `PackageRef`, `IOValue`) use `extra="forbid"` and contain only client-owned fields. Response models (`NodeResponse`, `AnnotationResponse`, `ReferenceResponse`, `ExecutionResultResponse`) use `extra="ignore"` and add server-generated (`creator_*`, `creation_timestamp`, execution result `id`) and server-derived (`used_by`, `connections`, `ReferenceResponse.artifact_type`) fields
- **One definition per field**: shared fields live in private `_…Fields` base classes, generic over the annotation/reference type where request and response differ (`_NodeFields[AnnT, RefT]`). Add a client-owned field to the base, a server-owned one to the response model only. Never redefine a field in a subclass (pyright strict rejects narrowing overrides)
- **Public surface**: everything is defined in `_models.py` and exported from `__init__.py` (`__all__`); consumers import from `sim_atlas_models` only
- **Wire compatibility**: a change here changes the JSON both sides send and accept. Node ids are content hashes (ADR-0005), so never change what parsers put into `source_code`/`hash` through a model change
- **Tests**: `tests/test_field_ownership.py` derives the server-owned fields from the models (`set(Response.model_fields) - set(Request.model_fields)`); add a new request/response pair to its `PAIRS` table and new request models to `REQUEST_SAMPLES`
- **Python floor 3.11** (the toolkit's); do not use 3.12-only syntax such as PEP 695 generics
- **Versioning**: released in lockstep with backend and toolkit; every dependent pins `sim-atlas-models==<version>` exactly (backend now, toolkit from #222); `scripts/release` bumps all three and rewrites every pin

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
