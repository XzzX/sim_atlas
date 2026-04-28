---
status: accepted
date: 2026-04-28
deciders: Sebastian Eibl
scope: backend
---

# Layered settings loading with XDG-inspired priority order

## Context and Problem Statement

The backend requires runtime configuration (JWT secrets, LLM API keys, VoyageAI key, model
names, etc.). Previously, the only configuration source was a `.env` file in the working
directory, meaning every deployment had to manage a single flat file. There was no way for
system administrators to set site-wide defaults, no per-user overrides without editing the
shared file, and no clear documentation of the load order.

The question is: how should the backend discover and merge configuration from multiple
sources while keeping a predictable, documented priority order?

## Considered Options

* Keep `.env`-only loading
* XDG Base Directory Specification with TOML files
* Explicit directory-based layering (`/etc/sim_atlas/`, `~/.sim_atlas/`, `.sim_atlas/`) with TOML files
* Python `dynaconf` or similar third-party configuration library

## Decision Outcome

Chosen option: **explicit directory-based layering with TOML files**, implemented via
`pydantic-settings`' built-in `TomlConfigSettingsSource` and `settings_customise_sources()`.

The loading order from lowest to highest priority is:

| Priority | Source | Path |
|---|---|---|
| 5 (lowest) | System config | `/etc/sim_atlas/config.toml` |
| 4 | User config | `~/.sim_atlas/config.toml` |
| 3 | Working-directory config | `.sim_atlas/config.toml` |
| 2 | `.env` file | `.env` in working directory |
| 1 (highest) | Environment variables | OS environment |

A value set at a higher-priority source always wins. All sources are optional; missing files
are silently skipped.

### Consequences

* Good, because system operators can set site-wide defaults without touching user files.
* Good, because users can override site-wide defaults without write access to `/etc`.
* Good, because project-local overrides (`.sim_atlas/config.toml`) work for per-repository
  setups, consistent with other developer-tooling conventions.
* Good, because the `.env` fallback preserves full backward compatibility for existing
  deployments.
* Good, because `pydantic-settings` handles all merging natively — no additional library
  is needed beyond a `[toml]` extra on the existing dependency.
* Good, because the priority order is explicit, documented here, and visible in `settings.py`.
* Neutral, because `pydantic-settings[toml]` requires `tomli`/`tomllib` at runtime
  (already available in Python ≥ 3.11; added as a dependency extra).
* Bad, because three config paths must now be communicated to operators in deployment docs.

## Pros and Cons of the Options

### Keep `.env`-only loading

* Good, because simplest possible approach.
* Bad, because no site-wide defaults without editing per-user files.
* Bad, because no clean separation between system, user, and project configuration.

### XDG Base Directory Specification

* Good, because follows a well-established Linux standard.
* Bad, because XDG is less familiar to scientific computing users and operators compared to
  a simple home-directory convention.
* Bad, because `XDG_CONFIG_DIRS` is colon-separated and needs manual parsing.
* Neutral, because the benefit over explicit paths is marginal for a non-desktop application.

### `dynaconf` or similar

* Good, because feature-rich (environments, secrets backends, remote configs).
* Bad, because introduces a heavyweight dependency and its own configuration DSL.
* Bad, because `pydantic-settings` already provides everything needed.
