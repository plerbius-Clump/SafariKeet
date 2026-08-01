from __future__ import annotations

import argparse
import http.client
import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .engines import PARAKEET_110M


def _platform_class(system: str, machine: str) -> str:
    if system == "Darwin" and machine in {"arm64", "aarch64"}:
        return "macos-apple-silicon"
    if system == "Darwin":
        return "macos-intel"
    return "other"


def _memory_bytes(system: str) -> int | None:
    if system != "Darwin":
        return None
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        return int(result.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _memory_tier(size: int | None) -> str:
    if size is None:
        return "unknown"
    gib = size / (1024**3)
    if gib < 8:
        return "low"
    if gib < 24:
        return "standard"
    return "high"


def _disk_tier(free: int) -> str:
    return "low" if free < 8 * 1024**3 else "ok"


def _model_cached(repo: str = PARAKEET_110M) -> bool:
    snapshots = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / ("models--" + repo.replace("/", "--"))
        / "snapshots"
    )
    try:
        return snapshots.is_dir() and any(snapshots.iterdir())
    except OSError:
        return False


def capability_report() -> dict[str, Any]:
    system = platform.system()
    platform_class = _platform_class(system, platform.machine())
    tools = {
        name: shutil.which(name) is not None
        for name in ("uv", "node", "npm", "ffmpeg", "tailscale")
    }
    model_cached = _model_cached()
    live_candidate = platform_class == "macos-apple-silicon"
    prerequisites = tools["uv"] and tools["node"] and tools["npm"] and tools["ffmpeg"]
    return {
        "schema": 1,
        "privacy": "scrubbed",
        "platform": platform_class,
        "memory": _memory_tier(_memory_bytes(system)),
        "disk": _disk_tier(shutil.disk_usage(Path.cwd()).free),
        "tools": tools,
        "model_cached": model_cached,
        "recommended_profile": "live-mlx" if live_candidate else "unsupported",
        "setup_ready": bool(live_candidate and prerequisites),
        "live_ready_after_setup": bool(live_candidate and prerequisites and model_cached),
    }


def _local_app_ready(port: int) -> bool:
    """Check the loopback service without placing its address in a report."""
    try:
        connection = http.client.HTTPConnection("localhost", port, timeout=2)
        connection.request("GET", "/api/health")
        response = connection.getresponse()
        response.read()
        connection.close()
        return response.status == 200
    except (OSError, http.client.HTTPException):
        return False


def _tailscale_json(arguments: list[str]) -> dict[str, Any] | None:
    executable = os.environ.get("SAFARAKEET_TAILSCALE_CLI") or shutil.which("tailscale")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, *arguments],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _proxy_matches_local_port(proxy: object, local_port: int) -> bool:
    if not isinstance(proxy, str):
        return False
    parsed = urlparse(proxy)
    try:
        port = parsed.port
    except ValueError:
        return False
    return parsed.scheme == "http" and parsed.hostname == "localhost" and port == local_port


def _serve_url(configuration: dict[str, Any], local_port: int, https_port: int) -> str | None:
    tcp = configuration.get("TCP")
    web = configuration.get("Web")
    if not isinstance(tcp, dict) or not isinstance(web, dict):
        return None

    for listener, site in web.items():
        if not isinstance(listener, str) or not isinstance(site, dict):
            continue
        host, separator, port_text = listener.rpartition(":")
        if not separator or not host or not port_text.isdecimal():
            continue
        port = int(port_text)
        if port != https_port:
            continue
        listener_config = tcp.get(str(port))
        if not isinstance(listener_config, dict) or listener_config.get("HTTPS") is not True:
            continue
        handlers = site.get("Handlers")
        if not isinstance(handlers, dict):
            continue
        if any(
            isinstance(handler, dict) and _proxy_matches_local_port(handler.get("Proxy"), local_port)
            for handler in handlers.values()
        ):
            return f"https://{host}:{port}/"
    return None


def connection_report(port: int | None = None, https_port: int | None = None) -> dict[str, Any]:
    """Return ephemeral sharing state; callers must not persist or log its URL."""
    if port is None:
        try:
            port = int(os.environ.get("SAFARAKEET_PORT", "8765"))
        except ValueError:
            port = 8765
    if https_port is None:
        try:
            https_port = int(os.environ.get("SAFARAKEET_HTTPS_PORT", "8443"))
        except ValueError:
            https_port = 8443

    if not _local_app_ready(port):
        return {"state": "app-unreachable"}

    status = _tailscale_json(["status", "--json"])
    if status is None:
        return {"state": "tailscale-unavailable"}
    if status.get("BackendState") != "Running":
        return {"state": "tailscale-disconnected"}

    serve = _tailscale_json(["serve", "status", "--json"])
    if serve is None:
        return {"state": "serve-unavailable"}
    url = _serve_url(serve, port, https_port)
    if url is None:
        return {"state": "serve-not-configured"}
    return {"state": "ready", "private_https_url": url}


def _human(report: dict[str, Any]) -> str:
    missing = [name for name, available in report["tools"].items() if not available]
    lines = [
        f"platform: {report['platform']}",
        f"memory: {report['memory']}",
        f"disk: {report['disk']}",
        f"recommended profile: {report['recommended_profile']}",
        f"model cached: {'yes' if report['model_cached'] else 'no'}",
        f"missing tools: {', '.join(missing) if missing else 'none'}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a privacy-scrubbed capability report")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = parser.parse_args()
    report = capability_report()
    print(json.dumps(report, sort_keys=True) if args.json else _human(report))


if __name__ == "__main__":
    main()
