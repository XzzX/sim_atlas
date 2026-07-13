---
name: run
description: Launch and drive the sim_atlas backend + frontend to verify a change end-to-end — starts the FastAPI backend, seeds it with real data via the e2e dummy_module + toolkit upload path, starts the frontend dev server, and drives it with a browser. Use when asked to run, start, preview, or manually verify the app, or to confirm a frontend/backend change actually works before reporting done.
---

# Running sim_atlas end-to-end

Two servers (backend + frontend), seeded with real data through the actual toolkit
upload path — not fabricated storage JSON. Always start long-running servers with the
harness's `run_in_background`, never raw shell `&` (see Gotchas).

## 1. Backend

```bash
cd backend && uv run sim-atlas   # run_in_background
```

- Port 8000. On first run, if no config file exists, auto-generates a JWT secret and
  writes `.sim_atlas_config.toml` in the working directory — no manual config needed.
- Storage (`artifacts.json`) is created in that same working directory and starts empty.
- Poll for readiness: `curl -sf http://127.0.0.1:8000/api/v1/filter_options`.

## 2. Seed data — reuse the real e2e fixture, don't fabricate JSON

[`.github/workflows/e2e.yml`](../../../.github/workflows/e2e.yml) is CI's own recipe for
populating a fresh backend: mint a JWT, then upload
[`e2e/dummy_module`](../../../e2e/dummy_module) through the real toolkit CLI. This exercises
the actual ingestion pipeline and produces 5 real artifacts across two real categories
(`dummy_module>functions`, `dummy_module>flowrep`) — including a workflow with 3 execution
results.

Run [`seed.sh`](seed.sh) (wraps the three steps below), or do it by hand:

```bash
TOKEN=$(cd backend && uv run sim-atlas-access-token "Dev" "dev@example.com")
cd e2e && uv venv --python=3.12   # skip if e2e/.venv already exists
uv pip install dummy_module/. ../toolkit/.
uv run sim-atlas-upload dummy_module dummy_module.flowrep \
  --api-url http://127.0.0.1:8000/api/v1 \
  --api-token "$TOKEN" \
  --module-allow flowrep
```

Re-running this against an already-seeded backend is safe — the toolkit reports each
already-present artifact as a conflict (`0 created, N conflicts`) and exits 0 rather than
erroring. Pass `--update-existing` if you actually want to overwrite existing nodes.

## 3. Frontend

```bash
cd frontend && npm run dev   # run_in_background
```

- Port 5173. Already proxies `/api` and `/ide` to `:8000`
  ([`vite.config.ts`](../../../frontend/vite.config.ts)) — no proxy setup needed.
- Open `http://localhost:5173/`.

**Alternative, production-parity only**: `npm run build`, copy `frontend/dist/*` into
`backend/src/sim_atlas/static/frontend/`, then hit `:8000/` directly. This is what the
committed e2e Playwright suite targets
([`e2e/playwright.config.ts`](../../../e2e/playwright.config.ts) `baseURL`) and what's
actually shipped in the backend package. Heavier — only do this when verifying the exact
built bundle, not while iterating on source.

## 4. Drive it

Prefer `chromium-cli` if available (see the global `run` skill). Verified fallback in a
container without it:

```bash
npm install playwright --no-save
npx playwright install chromium --with-deps   # one-time
```

Then a throwaway `.mjs` script:

```js
import { chromium } from "playwright";
const browser = await chromium.launch({ args: ["--no-sandbox"] });
const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
await page.goto("http://localhost:5173/");
await page.waitForSelector("text=Simulation Atlas");
await page.screenshot({ path: "screenshot.png" });
await browser.close();
```

To run the **committed** regression suite instead of ad hoc driving (needs the build+copy
step above first, since it targets `:8000`, not the Vite dev server):

```bash
cd e2e && npm ci && npx playwright install --with-deps chromium && npx playwright test
```

## Gotchas

- **Use `run_in_background`, not `&`.** An ad hoc-backgrounded dev server (and its `/tmp`
  scratch files) was silently lost mid-session to an environment reset with no signal.
  Harness-tracked background tasks instead fail loudly (`<task-notification
  status="failed"/"stopped">`) and can be cleanly stopped with `TaskStop`.
- Re-seeding an already-populated backend is safe — see step 2 (no-ops as conflicts, exit 0).
- `search_hybrid` ([`file_system_storage.py`](../../../backend/src/sim_atlas/file_system_storage.py))
  silently falls back to keyword-only ranking when no embedding provider is configured —
  expected, not a bug.
- `chromium-cli` may not be preinstalled in a given container; the Playwright fallback above
  is verified working (needs `apt-get`-installable system deps, handled by `--with-deps`).
