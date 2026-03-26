---
status: accepted
date: 2026-03-26
deciders: Sebastian Eibl
scope: backend
---

# FastAPI serves frontend assets as static files

## Context and Problem Statement

The project produces two compiled frontend artefacts: the search portal (`frontend/`) and
the web IDE (`web_ide/`). These must be served to users over HTTP. The question is whether
to introduce a dedicated web server (Nginx, Caddy) or to serve the static files from within
the FastAPI process itself.

## Considered Options

* Serve static files via FastAPI's `StaticFiles` mount
* Add Nginx or Caddy as a reverse proxy that serves static files and proxies API requests

## Decision Outcome

Chosen option: **serve static files via FastAPI `StaticFiles`**, because it eliminates a
deployment dependency during development and in single-host deployments. The built frontend
assets are copied into `backend/static/` and mounted at `/` (search portal) and `/ide`
(web IDE) respectively. A single `uvicorn` process serves everything.

### Consequences

* Good, because there is a single deployable artefact — the backend container — with no
  external static server required.
* Good, because local development matches production: `uv run uvicorn app.main:app` serves
  the full application.
* Neutral, because for high-traffic deployments a reverse proxy (Nginx) in front of Uvicorn
  would be preferred; this can be added without changing the backend code.
