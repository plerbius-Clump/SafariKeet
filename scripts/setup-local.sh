#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
profile=""
prefetch_model=false
build_frontend=false

while [ "$#" -gt 0 ]; do
  case "$1" in
    --profile)
      shift
      profile=${1:-}
      ;;
    --prefetch-model)
      prefetch_model=true
      ;;
    --build)
      build_frontend=true
      ;;
    *)
      printf 'Unknown option: %s\n' "$1" >&2
      exit 2
      ;;
  esac
  shift
done

if [ "$profile" != "live-mlx" ]; then
  printf 'Choose the supported profile with: --profile live-mlx\n' >&2
  exit 2
fi

cd "$project_dir"
platform_class=$(python3 -c 'from app.backend.doctor import capability_report; print(capability_report()["platform"])')
if [ "$platform_class" != "macos-apple-silicon" ]; then
  printf 'The live-mlx profile requires macOS on Apple silicon.\n' >&2
  exit 1
fi

missing=""
for tool in uv node npm ffmpeg; do
  if tool_location=$(command -v "$tool" 2>&1); then
    :
  else
    missing="$missing $tool"
  fi
done
if [ -n "$missing" ]; then
  printf 'Missing required tools:%s\n' "$missing" >&2
  printf 'Ask before installing system packages, then rerun setup.\n' >&2
  exit 1
fi

uv sync --extra dev

if [ "$prefetch_model" = true ]; then
  HF_HUB_DISABLE_PROGRESS_BARS=1 uv run python - <<'PY'
from parakeet_mlx import from_pretrained

from app.backend.engines import PARAKEET_110M

from_pretrained(PARAKEET_110M)
print("local model: ready")
PY
fi

if [ "$build_frontend" = true ]; then
  npm --prefix app/frontend ci
  npm --prefix app/frontend run build
fi

printf 'local setup: ready\n'
