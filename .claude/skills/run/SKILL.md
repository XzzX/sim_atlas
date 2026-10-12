---
name: run
description: Launch and drive the sim_atlas backend + frontend to verify a change end-to-end — starts the FastAPI backend, seeds it with real data via the e2e dummy_module + toolkit upload path, starts the frontend dev server, and drives it with a browser. Use when asked to run, start, preview, or manually verify the app, or to confirm a frontend/backend change actually works before reporting done.
---

# Running sim_atlas end-to-end

Two servers (backend + frontend), seeded with real data through the actual toolkit
upload path — not fabricated storage JSON. Everything goes through the repo's
[`scripts/`](../../../scripts/README.md), which CI uses too. Always start long-running
servers with the harness's `run_in_background`, never raw shell `&` (see Gotchas).

## 1. Setup (once per checkout)

```bash
scripts/setup
```

Installs all dependencies (`scripts/bootstrap`) and writes `backend/.sim_atlas_config.toml`
with a generated JWT secret if no config exists. After pulling new commits, re-run
`scripts/bootstrap`.

## 2. Start the servers

```bash
scripts/server   # run_in_background
```

- Backend on :8000, Vite dev server on :5173. Vite already proxies `/api` and `/ide` to
  `:8000` ([`vite.config.ts`](../../../frontend/vite.config.ts)).
- Storage (`backend/artifacts.json`) persists between runs; it starts empty on a fresh checkout.
- If either server dies, the script stops the other one and exits 1, so the background task
  reports the failure.
- Poll for readiness: `curl -sf http://127.0.0.1:8000/api/v1/filter_options` and
  `curl -sf http://localhost:5173/`.
- Open `http://localhost:5173/`.

**Production parity**: `scripts/server --static` builds both SPAs into the backend
(`scripts/build`) and serves everything from `:8000`. This is what the committed e2e
Playwright suite targets ([`e2e/playwright.config.ts`](../../../e2e/playwright.config.ts)
`baseURL`) and what ships in the backend package. Slower, so use it only when you need to
verify the exact built bundle, not while iterating on source.

## 3. Seed data

```bash
scripts/seed
```

Does what CI's [`e2e.yml`](../../../.github/workflows/e2e.yml) does: mints a JWT and uploads
[`e2e/dummy_module`](../../../e2e/dummy_module) through the real toolkit CLI (reinstalling the
current toolkit source first). Produces 5 real nodes across two categories
(`dummy_module>functions`, `dummy_module>flowrep`), including a workflow with 3 execution
results. Extra args are passed to `sim-atlas-upload` (e.g. `--update-existing`);
`SIM_ATLAS_API_URL` overrides the default `http://127.0.0.1:8000/api/v1`.

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

To run the **committed** regression suite instead of ad hoc driving (needs
`scripts/server --static` + `scripts/seed`, since it targets `:8000`, not the Vite dev server):

```bash
cd e2e && npx playwright install --with-deps chromium && npx playwright test
```

## Gotchas

- **Use `run_in_background`, not `&`.** An ad hoc-backgrounded dev server (and its `/tmp`
  scratch files) was silently lost mid-session to an environment reset with no signal.
  Harness-tracked background tasks instead fail loudly (`<task-notification
  status="failed"/"stopped">`) and can be cleanly stopped with `TaskStop`.
- Re-seeding an already-populated backend is safe: nodes are reported as existing, and
  execution results log `409 Conflict` errors (`3 errors` in the summary), but the
  command exits 0 and nothing is duplicated.
- `search_hybrid` ([`file_system_storage.py`](../../../backend/src/sim_atlas/file_system_storage.py))
  silently falls back to keyword-only ranking when no embedding provider is configured —
  expected, not a bug.
- `chromium-cli` may not be preinstalled in a given container; the Playwright fallback above
  is verified working (needs `apt-get`-installable system deps, handled by `--with-deps`).
