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
        FS["FileSystemStorage<br/>· In-memory dict[id→StoredArtifact]<br/>· Persisted as artifacts.json<br/>· Embeddings: gzip+base64 numpy array"]
        subgraph AI["External AI Services"]
            V["VoyageAI<br/>voyage-code-3<br/>(embeddings)"]
            L["OpenAI-compatible LLM<br/>(configurable URL)<br/>(docstring refinement)"]
        end
    end

    F["React Frontend  /<br/>· Keyword search<br/>· Semantic search<br/>· Faceted filter<br/>· NodeCard view"]
    W["Web IDE  /ide<br/>· Drag-drop canvas<br/>· ReactFlow + dagre<br/>· Import/export<br/>  PythonWorkflowDefinition JSON"]

    T -->|"POST /api/v1/artifacts  (JWT)"| B
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
    participant L as LLM (optional)
    participant B as Backend (FastAPI)
    participant S as FileSystemStorage

    R->>T: upload(obj) / upload_modules(modules)
    T->>T: inspect obj → parser picks FunctionRequest<br/>or WorkflowRequest, computes<br/>hash = SHA-256(source_code)
    T->>B: GET /api/v1/artifacts/{hash}
    alt artifact already exists
        B-->>T: 200 OK (existing artifact)
        Note over T: most parsers stop here,<br/>skipping LLM + upload
    else not found
        B-->>T: 404 Not Found
        opt llm_enabled
            T->>L: generate/refine docstring from source (+ dataflow graph for workflows)
            L-->>T: docstring
        end
        T->>B: POST /api/v1/artifacts (x-api-key: JWT)
        B->>B: validate JWT → extract creator
        B->>B: compose_artifact: id = request.id or<br/>SHA-256(source_code)
        B->>S: create_artifact(StoredArtifact)
        alt id already exists
            S-->>B: raise ArtifactAlreadyExistsError
            B-->>T: 409 Conflict (existing artifact)
        else hash already exists (different id)
            S-->>B: raise ArtifactDuplicateError
            B-->>T: 409 Conflict (existing artifact)
        else new artifact
            S->>S: update in-memory dict
            S->>S: flush to artifacts.json
            B-->>T: 201 Created (ArtifactResponse)
        end
    end
```

### Search Flow

```mermaid
sequenceDiagram
    actor U as User
    participant F as React Frontend
    participant B as Backend (FastAPI)
    participant S as FileSystemStorage
    participant E as Embedding Provider<br/>(fastembed local, or<br/>OpenAI/VoyageAI API)

    U->>F: enter query + set facet filters
    F->>B: POST /api/v1/search {query, filter, semantic, page, limit}
    alt semantic == false
        B->>S: search(): apply NodeFilter → keyword score
        Note right of S: score 1.0 if query in name+python_import<br/>score 0.8 if query in brief_description<br/>score 0.5 if query in docstring
        S-->>B: sorted, paginated SearchResults
    else semantic (default) → search_hybrid()
        alt no query, or embeddings_enabled == false
            B->>S: fall back to search() (keyword-only, same scoring as above)
            S-->>B: sorted, paginated SearchResults
        else query tokenizes to nothing ≥3 chars
            B->>E: create_embedding(query, input_type="query")
            E-->>B: query vector
            B->>S: search_semantic(): apply NodeFilter → cosine similarity only
            S-->>B: sorted, paginated SearchResults
        else
            B->>E: create_embedding(query, input_type="query")
            E-->>B: query vector
            B->>S: apply NodeFilter once, then rank two ways
            Note right of S: semantic rank: cosine similarity<br/>(nodes with an embedding only)<br/>keyword rank: token hit-count<br/>(tokens ≥3 chars, all filtered nodes)
            S->>S: RRF merge: score = 1/(60+sem_rank) + 1/(60+kw_rank)<br/>(0 for a side a node is absent from)
            S-->>B: sorted, paginated SearchResults
        end
    end
    B-->>F: ScoredSearchResponse (ScoredSearchItem[])
    F->>U: render NodeCard components
```

---

*End of document.*