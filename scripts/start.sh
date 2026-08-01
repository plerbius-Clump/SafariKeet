#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

cd "$project_dir"
./scripts/setup-local.sh --profile live-mlx --build
exec ./scripts/run.sh
