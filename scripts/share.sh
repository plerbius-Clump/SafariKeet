#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
local_port=${SAFARAKEET_PORT:-8765}
https_port=${SAFARAKEET_HTTPS_PORT:-8443}
command=${1:-status}

case "$local_port:$https_port" in
  *[!0-9:]* | :* | *:)
    printf 'SafaraKeet ports must be numeric.\n' >&2
    exit 2
    ;;
esac

connection_state() {
  python3 - "$local_port" "$https_port" <<'PY'
import sys

from app.backend.doctor import connection_report

print(connection_report(int(sys.argv[1]), int(sys.argv[2]))["state"])
PY
}

private_url() {
  python3 - "$local_port" "$https_port" <<'PY'
import sys

from app.backend.doctor import connection_report

report = connection_report(int(sys.argv[1]), int(sys.argv[2]))
print(report.get("private_https_url", ""))
PY
}

require_local_app() {
  state=$(connection_state)
  if [ "$state" = "app-unreachable" ]; then
    printf 'SafaraKeet is not responding locally. Start the local service first.\n' >&2
    exit 1
  fi
}

cd "$project_dir"

case "$command" in
  status)
    state=$(connection_state)
    case "$state" in
      ready) printf 'private HTTPS: ready\n' ;;
      *) printf 'private HTTPS: %s\n' "$state" ;;
    esac
    ;;
  start)
    require_local_app
    state=$(connection_state)
    if [ "$state" = "ready" ]; then
      printf 'private HTTPS: ready\n'
      exit 0
    fi
    if ! command -v tailscale >/dev/null 2>&1; then
      printf 'Tailscale is unavailable. Connect Tailscale, then try again.\n' >&2
      exit 1
    fi
    if command -v lsof >/dev/null 2>&1 && lsof -nP -iTCP:"$https_port" -sTCP:LISTEN >/dev/null 2>&1; then
      printf 'The requested private HTTPS port is already in use. Choose another SAFARAKEET_HTTPS_PORT.\n' >&2
      exit 1
    fi
    if ! tailscale serve --https="$https_port" --bg "http://localhost:$local_port" >/dev/null 2>&1; then
      printf 'Private HTTPS setup needs Tailscale approval or a healthy Tailscale connection. Complete that in Tailscale, then try again.\n' >&2
      exit 1
    fi
    state=$(connection_state)
    if [ "$state" != "ready" ]; then
      printf 'Private HTTPS was configured but could not be verified: %s\n' "$state" >&2
      exit 1
    fi
    printf 'private HTTPS: ready\n'
    ;;
  open)
    require_local_app
    url=$(private_url)
    if [ -z "$url" ]; then
      printf 'Private HTTPS is not ready. Run ./scripts/share.sh start first.\n' >&2
      exit 1
    fi
    if ! command -v open >/dev/null 2>&1; then
      printf 'Open the verified private HTTPS link from SafaraKeet settings.\n' >&2
      exit 1
    fi
    open "$url"
    printf 'private HTTPS: opened\n'
    ;;
  *)
    printf 'Usage: ./scripts/share.sh start|status|open\n' >&2
    exit 2
    ;;
esac
