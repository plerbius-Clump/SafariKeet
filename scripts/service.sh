#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
state_dir="$project_dir/.safarikeet"
service_file="$state_dir/service.plist"
service_label="org.safarikeet.local"
service_target="gui/$(id -u)/$service_label"
local_port=${SAFARAKEET_PORT:-8765}
service_host=${SAFARAKEET_HOST:-localhost}
tailscale_cli=${SAFARAKEET_TAILSCALE_CLI:-$(command -v tailscale 2>/dev/null || true)}
command=${1:-status}

case "$command" in
  check)
    if ! launchctl_location=$(command -v launchctl 2>&1); then
      printf 'local service: launchctl unavailable\n' >&2
      exit 1
    fi
    if [ ! -x "$project_dir/.venv/bin/uvicorn" ] || [ ! -f "$project_dir/app/frontend/dist/index.html" ]; then
      printf 'local service: setup required\n' >&2
      exit 1
    fi
    printf 'local service: ready to install\n'
    ;;
  install)
    mkdir -p "$state_dir"
    executable="$project_dir/.venv/bin/uvicorn"
    if [ ! -x "$executable" ] || [ ! -f "$project_dir/app/frontend/dist/index.html" ]; then
      printf 'Run setup with --build before installing the service.\n' >&2
      exit 1
    fi
    cat > "$service_file" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0"><dict>
  <key>Label</key><string>$service_label</string>
  <key>ProgramArguments</key><array>
    <string>$executable</string><string>app.backend.main:app</string>
    <string>--host</string><string>$service_host</string>
    <string>--port</string><string>$local_port</string>
  </array>
  <key>WorkingDirectory</key><string>$project_dir</string>
  <key>EnvironmentVariables</key><dict>
    <key>SAFARAKEET_TAILSCALE_CLI</key><string>$tailscale_cli</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$state_dir/service.log</string>
  <key>StandardErrorPath</key><string>$state_dir/service.log</string>
</dict></plist>
EOF
    if bootout_output=$(launchctl bootout "$service_target" 2>&1); then
      sleep 1
    fi
    launchctl bootstrap "gui/$(id -u)" "$service_file"
    printf 'local service: installed\n'
    ;;
  start)
    if launchctl print "$service_target" >/dev/null 2>&1; then
      launchctl kickstart -k "$service_target"
    elif [ -f "$service_file" ]; then
      launchctl bootstrap "gui/$(id -u)" "$service_file"
    else
      printf 'local service: not installed; run install first\n' >&2
      exit 1
    fi
    printf 'local service: started\n'
    ;;
  stop)
    if launchctl print "$service_target" >/dev/null 2>&1; then
      launchctl bootout "$service_target"
    fi
    printf 'local service: stopped\n'
    ;;
  status)
    if service_details=$(launchctl print "$service_target" 2>&1); then
      printf 'local service: running\n'
    else
      printf 'local service: not installed\n'
      exit 1
    fi
    ;;
  uninstall)
    bootout_output=$(launchctl bootout "$service_target" 2>&1) || true
    if [ -f "$service_file" ]; then
      mv "$service_file" "$state_dir/service.plist.disabled"
    fi
    printf 'local service: uninstalled; local state retained\n'
    ;;
  *)
    printf 'Usage: ./scripts/service.sh check|install|start|stop|status|uninstall\n' >&2
    exit 2
    ;;
esac
