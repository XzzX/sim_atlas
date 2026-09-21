[![License](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)
![PyPI - backend](https://img.shields.io/pypi/v/sim-atlas?label=backend)
![PyPI - toolkit](https://img.shields.io/pypi/v/sim-atlas-toolkit?label=toolkit)


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

### 1. Start the server via `uvx`

```bash
cd <sim-atlas>
uvx sim-atlas
```
On the first start the server will create a configuration file in the current working directory if it does not find one.

The API and both SPAs are now available at http://localhost:8000.

### 2. Generate an API token

Write access (uploading nodes) requires a JWT token:

```bash
cd <sim-atlas-env>
uvx --from sim-atlas sim-atlas-access-token "Your Name" "you@example.com"
export SIM_ATLAS_API_URL=http://localhost:8000/api/v1
export SIM_ATLAS_API_TOKEN=<token>
```

### 3. Upload nodes from a Python package

Load the environment with the modules you want to upload. Install the sim-atlas-toolkit into this environment. And upload the module.
For example:
```bash
uv pip install sim-atlas-toolkit
uv run sim-atlas-upload --recursive filesystem mypackage.mymodule
```

### 4. Explore your newely created nodes

Head over to the webinterface and explore the nodes you uploaded:  
http://localhost:8000

## Use from Claude Code

Sim Atlas exposes a read-only MCP tool surface aimed at CLI coding agents, so you
can write plain Python against the catalog without leaving the terminal (see
[ADR-0019](docs/adr/0019-mcp-python-tool-surface.md)). It is independent of the
Web IDE's agent — no LLM key is needed on the server for this path.

### 1. Register the server

```bash
claude mcp add --transport http sim-atlas http://localhost:8000/mcp/
```

Reads are public, so no token is required. Four tools become available:

| Tool | Answers |
|---|---|
| `search_functions` | "what does X?" |
| `find_by_signature` | "what returns a temperature in K?" |
| `get_function` | "how exactly do I call it, and what do I need installed?" |
| `get_workflow_source` | "show me a pipeline that uses it" |

Results come back as Python: a call signature, the exact `from ... import ...`
line, and an install hint for the distribution the function was parsed from
(PyPI and conda).

### 2. Install the skill (recommended)

The tools work on their own, but the skill tells the agent *when* to reach for
the catalog and how to handle a package that is not installed locally:

```bash
mkdir -p ~/.claude/skills
cp -r skills/sim-atlas ~/.claude/skills/
```

The `references/` directory has to come along: the skill loads its syntax guides
for flowrep and executorlib from there — `cp -r` on the whole `sim-atlas`
directory takes care of that.

Claude Code checks whether a package is importable before writing an import, and
proposes an install command matched to your project's package manager (uv, pixi,
conda or pip) for you to confirm. The server never inspects or changes your
environment. For a pipeline it asks whether you want plain Python, a flowrep
workflow or an executorlib pipeline rather than picking for you.
