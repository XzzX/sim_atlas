#!/usr/bin/env bash
# Seed a running sim_atlas backend with the e2e dummy_module fixture (see SKILL.md).
# Usage: seed.sh [api-base-url]   (default: http://127.0.0.1:8000/api/v1)
set -euo pipefail

API_URL="${1:-http://127.0.0.1:8000/api/v1}"

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../../.." && pwd)

TOKEN=$(cd "$REPO_ROOT/backend" && uv run sim-atlas-access-token "Dev" "dev@example.com")

cd "$REPO_ROOT/e2e"
if [ ! -d .venv ]; then
  uv venv --python=3.12
fi
uv pip install dummy_module/. ../toolkit/.

uv run sim-atlas-upload dummy_module dummy_module.flowrep \
  --api-url "$API_URL" \
  --api-token "$TOKEN" \
  --module-allow flowrep
