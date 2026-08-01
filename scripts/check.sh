#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

uv run pytest
npm --prefix app/frontend test
npm --prefix app/frontend run build
