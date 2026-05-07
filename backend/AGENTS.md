# backend

FastAPI REST API with MCP tool exposure and AI integration.

## Commands

```bash
uv run pytest                           # run tests
uv run coverage run -m pytest           # run tests with coverage
uv run ruff check .                     # lint
uv run ruff format --check .            # check formatting
uv run pyright                          # type-check (strict mode)
```

## Key Patterns

- **Storage**: always interact via `storage_interface.py` (`StorageInterface`), never directly via `file_system_storage.py`
- **Dependency injection**: use FastAPI `Depends()` for storage, settings, and auth — see existing routes in `main.py`
- **Models**: Pydantic v2; all schemas defined in `models.py`
- **Auth**: JWT-based write access in `security.py`; reads are public
- **MCP**: routes are exposed as MCP tools via `fastapi-mcp`; keep route signatures clean (they double as tool signatures)
- **AI**: embeddings via VoyageAI (`voyage_ai.py`); LLM calls via OpenAI-compatible API (`ai.py`); streaming agent responses in `agent/`
- **Config**: all settings via `settings.py` (`pydantic-settings`); never hardcode secrets or URLs

## Libraries

- **pydantic**: [Documentation](https://pydantic.dev/docs/validation/latest/llms.txt)
- **pydantic-settings**: [Documentation](https://pydantic.dev/docs/validation/latest/llms.txt)
