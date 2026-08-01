#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
local_port=${SAFARAKEET_PORT:-8765}

cd "$project_dir"
exec uv run uvicorn app.backend.main:app --host localhost --port "$local_port"
