# toolkit

Client-side library for parsing installed Python packages and uploading simulation node metadata to the backend.

## Commands

```bash
uv run ruff check .      # lint
uv run ruff format --check .  # check formatting
uv run pyright           # type-check (strict mode)
```

No test suite yet — lint and type-check are the CI gates.

## Key Patterns

- **Entry point**: `node_store.py` (`NodeStore`) orchestrates the full pipeline: module inspection → metadata extraction → HTTP upload
- **Parser plugins**: add new parsers in `parsers/` following the existing modules (`pyiron_core.py`, `pyiron_workflow.py`, `python_function.py`, `python_workflow_definition.py`)
- **Core parsing**: `parser.py` uses Python `inspect` API and recursive module traversal; parsers receive a module object and return a list of `Node` metadata objects
- **Schema**: `models.py` defines the shared `Node` model; must stay compatible with `python-workflow-definition` and the backend's Pydantic schemas
- **No server code**: this package runs entirely on the client machine; never adds server-side dependencies
