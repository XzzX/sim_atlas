# Sim Atlas

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.122%2B-009688)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB)](https://react.dev/)
[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)

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
uv pip install <sim-atlas-clone>/backend/.
```

### 2. Configure and start the backend

```bash
cd <sim-atlas-env>
uv run sim-atlas-server
```
The server will exit gracefully telling you to setup the config. Adapt the config.
```bash
uv run sim-atlas-server
```

The API and both SPAs are now available at `http://localhost:8000`.
Interactive API docs: `http://localhost:8000/docs`

### 3. Generate an API token

Write access (uploading nodes) requires a JWT token:

```bash
cd <sim-atlas-env>
uv run sim-atlas-access-token "Your Name" "you@example.com"
export SIM_ATLAS_API_URL=http://localhost:8000/api/v1
export SIM_ATLAS_API_TOKEN=<token>
```

### 4. Upload nodes from a Python package

Load the environment with the modules you want to upload. Install the sim-atlas-toolkit. And upload the module
```bash
uv pip install <sim-atlas-clone>/toolkit/.
uv run sim-atlas-upload mypackage.mymodule
```
