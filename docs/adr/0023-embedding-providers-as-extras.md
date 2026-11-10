---
status: accepted
date: 2026-11-10
deciders: Sebastian Eibl
scope: backend
---

# Embedding providers as optional extras, loaded lazily

## Context and Problem Statement

The backend listed `fastembed` (with `onnxruntime`), `openai` and `voyageai` as hard
dependencies, about 110 MB. `embedding.py` imported all three at module level, and every
import of the app went through it. As a result, every install and every server start paid
for all three providers, even though a deployment uses at most one and keyword-only search
needs none. `embedding.py` and `FileSystemStorage` also read `load_settings()` directly. That
made them unusable outside the server: importing `settings` writes a config file on first
load.

## Considered Options

* Keep the providers as hard dependencies
* One extra per provider, plus an aggregate `ai`/`all` extra
* One extra per provider, no aggregate extra

## Decision Outcome

Chosen option: **one extra per provider, no aggregate extra.**

* Extras `fastembed`, `openai` and `voyageai`. `sim-atlas[fastembed]` is the documented
  default install, and the generated config file keeps `embedding_provider = "fastembed"`.
* Each provider's package is imported inside its own factory in `embedding.py`, on first
  use. If the import fails, the factory raises `AINotConfiguredError` with the install hint.
* `embedding.py` is settings-free. It takes a frozen `EmbeddingConfig` and returns a plain
  `np.ndarray`. `FileSystemStorage` takes `embedding_config` in its constructor, where `None`
  means keyword-only search. Only `get_storage_backend()` maps settings to that config.
* If the configured provider isn't usable (extra missing, or API key/model missing),
  `get_storage_backend()` logs a warning and the server falls back to keyword-only search
  instead of failing.

### Consequences

* Good: a core install is about 110 MB smaller, and `import sim_atlas.main` no longer loads
  onnxruntime or the provider SDKs.
* Good: embeddings and storage can be reused as a library, with no server stack and no config
  file.
* Bad: a plain `pip install sim-atlas` with the generated config serves keyword-only search
  until the extra is installed. The startup warning names the fix.
* CI runs a separate core-only job (`uv sync --group dev`, no extras) to keep this working.
