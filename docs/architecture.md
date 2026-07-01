# Software Architecture Document
## Sim Atlas — Simulation Node Search & Discovery Platform

**Version:** 0.2  
**Status:** Active  
**Date:** 2026-04-02

---

## 1. Overview

Sim Atlas is a search and discovery platform for simulation nodes — Python functions, workflow definitions, and pyiron nodes used in scientific computing. Users parse their locally installed Python packages or modules using the **toolkit** client library, then push the extracted metadata to a central server where it becomes searchable by all users via a **React search frontend**.

The system is structured as a **monorepo** containing four sub-packages: `backend`, `frontend`, `web_ide`, and `toolkit`.

---

## 2. Goals & Non-Goals

**Goals**
- Enable fast, faceted search over simulation node metadata (name, docstring, inputs/outputs with physical units and quantities)
- Support semantic search via AI-generated embeddings
- Never execute arbitrary user-provided code on the server
- Keep the server stateless with respect to parsing logic
- Expose a machine-readable MCP tool for AI agent integration
- Provide a visual drag-and-drop workflow composer

**Non-Goals**
- Code execution or sandboxing on the server
- Version control or diff tracking of parsed codebases
- Freshness guarantees — upstream source changes are silently stale (see ADR-0012)
- Multi-tenancy (writes are authenticated but reads are public for v0.1)

---

## 3. Repository Layout

```
sim_atlas/
├── backend/          Python package: sim-atlas-backend (FastAPI server)
├── frontend/         React SPA: keyword & semantic search portal
├── web_ide/          React SPA: visual workflow composer
├── toolkit/          Python package: sim-atlas-toolkit (parser + upload client)
└── docs/             Architecture docs, ADRs
```

The frontend and web_ide build artefacts are served as static files by the backend (see §4.2), producing a single deployable unit.

---

## 4. System Components

```mermaid
flowchart TD
    subgraph RM["Researcher's Machine"]
        T["sim-atlas-toolkit<br/>· Inspects Python env (inspect API)<br/>· plain functions, pyiron nodes,<br/>  workflow definitions<br/>· Serialises NodeRequest JSON"]
    end

    subgraph SRV["Server"]
        B["FastAPI Backend<br/>· JWT auth for write endpoints<br/>· CRUD for nodes<br/>· Keyword & semantic search<br/>· On-demand AI enrichment endpoint<br/>· MCP tool for semantic search<br/>· Serves frontend & web_ide SPAs"]
        FS["FileSystemStorage<br/>· In-memory dict[sha256→NodeMetadata]<br/>· Persisted as filesystem.json<br/>· Embeddings: gzip+base64 numpy array"]
        subgraph AI["External AI Services"]
            V["VoyageAI<br/>voyage-code-3<br/>(embeddings)"]
            L["OpenAI-compatible LLM<br/>(configurable URL)<br/>(docstring refinement)"]
        end
    end

    F["React Frontend  /<br/>· Keyword search<br/>· Semantic search<br/>· Faceted filter<br/>· NodeCard view"]
    W["Web IDE  /ide<br/>· Drag-drop canvas<br/>· ReactFlow + dagre<br/>· Import/export<br/>  PythonWorkflowDefinition JSON"]

    T -->|"POST /api/v1/nodes  (JWT)"| B
    B --> FS
    B -->|"REST API / MCP"| F
    B -->|"REST API / MCP"| W
```

---

## 5. Data Flow

### Upload Flow

```mermaid
sequenceDiagram
    actor R as Researcher
    participant T as sim-atlas-toolkit
    participant B as Backend (FastAPI)
    participant S as FileSystemStorage

    R->>T: NodeStore.upload(obj) / upload_module(module)
    T->>T: inspect obj → extract metadata
    T->>T: serialise to NodeRequest JSON
    T->>B: POST /api/v1/nodes (x-api-key: JWT)
    B->>B: validate JWT → extract creator
    B->>B: compute id = SHA-256(source_code)
    alt id already exists
        B-->>T: 409 Conflict
    else new node
        B->>S: create(NodeMetadata)
        S->>S: update in-memory dict
        S->>S: flush to filesystem.json
        B-->>T: 201 Created (id)
    end
```

### AI Enrichment Flow

```mermaid
sequenceDiagram
    actor O as Operator
    participant B as Backend (FastAPI)
    participant S as FileSystemStorage
    participant L as OpenAI-compatible LLM
    participant V as VoyageAI

    O->>B: POST /api/v1/enrich (x-api-key: JWT)
    B->>B: validate JWT
    B->>S: iterate all nodes
    loop for each node where ai_docstring is empty
        B->>L: chat completion(docstring, source_code)
        L-->>B: refined docstring
        B->>S: update node.ai_docstring
        S->>S: flush to filesystem.json
    end
    B-->>O: enrichment complete

    Note over O,V: Embedding generation is a separate step
    O->>B: (separate invocation / script)
    B->>V: embed(source_code + docstring, input_type="document")
    V-->>B: float32 embedding vector
    B->>S: update node.embedding
    S->>S: flush to filesystem.json
```

### Search Flow

```mermaid
sequenceDiagram
    actor U as User
    participant F as React Frontend
    participant B as Backend (FastAPI)
    participant S as FileSystemStorage
    participant V as VoyageAI

    U->>F: enter query + set facet filters
    F->>B: POST /api/v1/search {query, filter, semantic, page, limit}
    alt embeddings configured and semantic != false
        B->>V: embed(query, input_type="query")
        V-->>B: query vector
        B->>S: apply NodeFilter → RRF merge of cosine similarity + keyword rank
        S-->>B: sorted, paginated SearchResults
    else no embeddings, or semantic == false (keyword fallback)
        B->>S: apply NodeFilter → keyword score candidates
        Note right of S: score 1.0 if query in python_import<br/>score 0.5 if query in docstring
        S-->>B: sorted, paginated SearchResults
    end
    B-->>F: SearchResults (ScoredSearchItem[])
    F->>U: render NodeCard components
```

---

*End of document.*