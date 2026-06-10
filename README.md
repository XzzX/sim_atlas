[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

[![backend](https://github.com/XzzX/sim_atlas/actions/workflows/backend.yml/badge.svg?branch=main)](https://github.com/XzzX/sim_atlas/actions/workflows/backend.yml)
[![frontend](https://github.com/XzzX/sim_atlas/actions/workflows/frontend.yml/badge.svg?branch=main)](https://github.com/XzzX/sim_atlas/actions/workflows/frontend.yml)
[![toolkit](https://github.com/XzzX/sim_atlas/actions/workflows/toolkit.yml/badge.svg?branch=main)](https://github.com/XzzX/sim_atlas/actions/workflows/toolkit.yml)
[![web-ide](https://github.com/XzzX/sim_atlas/actions/workflows/web_ide.yml/badge.svg?branch=main)](https://github.com/XzzX/sim_atlas/actions/workflows/web_ide.yml)
[![e2e](https://github.com/XzzX/sim_atlas/actions/workflows/e2e.yml/badge.svg?branch=main)](https://github.com/XzzX/sim_atlas/actions/workflows/e2e.yml)

# Sim Atlas

Search and discovery platform for simulation nodes — Python functions, workflow definitions, and pyiron nodes used in scientific computing.

## Repository layout

```
sim_atlas/
├── backend/    FastAPI server (sim-atlas-backend)
├── frontend/   Search & discovery SPA, served at /
├── web_ide/    Visual workflow composer SPA, served at /ide
├── toolkit/    Client-side parser & upload library (sim-atlas-toolkit)
└── docs/       Architecture docs and ADRs
```

## How it works

1. Researchers run the **toolkit** on their machine to parse their Python packages and push node metadata to the server.
2. The **backend** stores metadata, generates AI embeddings and AI-refined docstrings on demand, and exposes a REST API and MCP tool.
3. The **frontend** and **web_ide** are React SPAs built into the backend's static directory and served by it.

## Quickstart

### 1. Clone the repository and install it into a venv

```bash
cd <sim-atlas-env>
uv venv --python=3.12
uv pip install sim-atlas
```

### 2. Configure and start the backend

```bash
cd <sim-atlas-env>
uv run sim-atlas
```
On the first start the server will create a configuration file in the current working directory if it does not find one.

The API and both SPAs are now available at `http://localhost:8000`.

### 3. Generate an API token

Write access (uploading nodes) requires a JWT token:

```bash
cd <sim-atlas-env>
uv run sim-atlas-access-token "Your Name" "you@example.com"
export SIM_ATLAS_API_URL=http://localhost:8000/api/v1
export SIM_ATLAS_API_TOKEN=<token>
```

### 4. Upload nodes from a Python package

Load the environment with the modules you want to upload. Install the sim-atlas-toolkit into this environment. And upload the module.
For example:
```bash
uv pip install sim-atlas-toolkit
uv run sim-atlas-upload --recursive filesystem mypackage.mymodule
```
