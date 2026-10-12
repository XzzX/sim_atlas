# scripts

Scripts folder following [Scripts to Rule Them All](https://github.blog/engineering/scripts-to-rule-them-all/):
one entry point per task, used the same way by developers, CI, the devcontainer and
coding agents. Every script can be run from any directory.

| Script | What it does |
|---|---|
| `scripts/bootstrap` | Installs or updates all dependencies: `uv sync` in `backend/` and `toolkit/`, `npm ci` in `frontend/`, `web_ide/` and `e2e/`. Safe to re-run; run it after pulling. |
| `scripts/setup` | First-time setup: runs `bootstrap`, then writes `backend/.sim_atlas_config.toml` with a generated JWT secret if no config file exists. |
| `scripts/server` | Starts the backend on :8000 and the frontend dev server on :5173 (proxies `/api` and `/ide` to the backend). Stops both on Ctrl+C or when either one dies. |
| `scripts/server --static` | Runs `build`, then serves the API and both web apps from the backend on :8000, as in production. |
| `scripts/build` | Builds `frontend/` and `web_ide/` into `backend/src/sim_atlas/static/`. Run it before `uv build` when releasing the backend. |
| `scripts/seed` | Uploads the `e2e/dummy_module` fixture to a running backend through the real toolkit CLI (5 nodes, including a workflow with execution results). Extra arguments go to `sim-atlas-upload`; `SIM_ATLAS_API_URL` overrides the default `http://127.0.0.1:8000/api/v1`. |

## Getting started

```bash
scripts/setup    # once
scripts/server   # http://localhost:5173
scripts/seed     # in a second terminal, to get some sample data
```

## Requirements

`uv` and `npm` (Node 24) must be on `PATH`; the scripts do not install them.
The devcontainer installs `uv` and runs `scripts/setup` automatically.

## Not provided

`update`, `test`, `cibuild` and `console` from the original pattern are left out on
purpose. The backend has no database migrations, so `update` would be the same as
`bootstrap`, and each package already runs its own lint and test commands (see the
`CLAUDE.md` files and `.github/workflows/`).
