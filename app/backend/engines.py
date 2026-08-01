from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

PARAKEET_110M = "mlx-community/parakeet-tdt_ctc-110m"
PARAKEET_06B_V3 = "mlx-community/parakeet-tdt-0.6b-v3"
PARAKEET_06B_V2 = "mlx-community/parakeet-tdt-0.6b-v2"


@dataclass(frozen=True)
class EngineFinding:
    id: str
    name: str
    available: bool
    runnable: bool
    priority: int
    detail: str
    model: str | None = None
    test_command: str | None = None
    install_hint: str | None = None
    informational: bool = False

    def public(self) -> dict[str, Any]:
        return asdict(self)


def _run(command: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


@lru_cache(maxsize=1)
def _brew_prefix() -> Path | None:
    brew = shutil.which("brew")
    result = _run([brew, "--prefix"]) if brew else None
    return Path(result.stdout.strip()) if result and result.returncode == 0 else None


def _which(*names: str, source_candidates: Iterable[Path] = ()) -> str | None:
    for name in names:
        if binary := shutil.which(name):
            return binary
    interpreter_bin = Path(sys.executable).parent
    for name in names:
        candidate = interpreter_bin / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    for candidate in source_candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    prefix = _brew_prefix()
    if prefix:
        for name in names:
            candidate = prefix / "bin" / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None


def _cached_hf_model(repo: str) -> bool:
    model_dir = Path.home() / ".cache" / "huggingface" / "hub" / (
        "models--" + repo.replace("/", "--")
    )
    snapshots = model_dir / "snapshots"
    try:
        return snapshots.is_dir() and any(snapshots.iterdir())
    except OSError:
        return False


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _process_present(pattern: str) -> bool:
    result = _run(["pgrep", "-if", pattern], timeout=2)
    return bool(result and result.returncode == 0)


def _model_roots(binary: str | None, family: str) -> list[Path]:
    home = Path.home()
    roots = [
        home / f"{family}-models",
        home / f"{family}.cpp" / "models",
        home / ".cache" / family,
        home / ".cache" / "huggingface" / "hub",
        home / ".local" / "share" / f"{family}.cpp" / "models",
    ]
    if binary:
        executable = Path(binary).resolve()
        roots.extend(
            [
                executable.parent / "models",
                executable.parent.parent / "share" / f"{family}.cpp" / "models",
                executable.parent.parent / "share" / family / "models",
            ]
        )
    return list(dict.fromkeys(roots))


def _find_model(
    roots: Iterable[Path], *, suffixes: tuple[str, ...], terms: tuple[str, ...]
) -> Path | None:
    matches: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for current, directories, files in os.walk(root):
                relative_depth = len(Path(current).relative_to(root).parts)
                if relative_depth >= 7:
                    directories.clear()
                directories[:] = [name for name in directories if name not in {".git", "node_modules"}]
                for filename in files:
                    lowered = filename.lower()
                    if lowered.endswith(suffixes) and any(term in lowered for term in terms):
                        matches.append(Path(current) / filename)
        except OSError:
            continue
    if not matches:
        return None
    return min(
        matches,
        key=lambda path: (
            0 if "110m" in path.name.lower() or "tdt_ctc" in path.name.lower() else 1,
            len(path.name),
        ),
    )


def _macparakeet_probe(binary: str) -> tuple[bool, bool, bool, str]:
    health = _run([binary, "health", "--json"])
    if not health or health.returncode != 0:
        return False, False, False, "binary found; JSON health check failed"
    health_text = f"{health.stdout}\n{health.stderr}"
    models = _run([binary, "models", "list", "--json"])
    help_result = _run([binary, "transcribe", "--help"])
    combined = f"{health_text}\n{models.stdout if models else ''}".lower()
    supports_110m = "110m" in combined or "tdt_ctc" in combined
    supports_model_flag = bool(help_result and "--model" in f"{help_result.stdout}\n{help_result.stderr}")
    return True, supports_110m, supports_model_flag, "health check passed"


def _whisper_model(binary: str | None = None) -> Path | None:
    return _find_model(
        _model_roots(binary, "whisper"),
        suffixes=(".bin",),
        terms=("ggml-", "whisper"),
    )


def _parakeet_cpp_model(binary: str | None = None) -> Path | None:
    return _find_model(
        _model_roots(binary, "parakeet"),
        suffixes=(".gguf",),
        terms=("parakeet", "110m", "tdt_ctc", "0.6b"),
    )


def _parakeet_port_presence() -> str | None:
    model = _find_model(
        _model_roots(None, "parakeet"),
        suffixes=(".onnx", ".gguf"),
        terms=("parakeet", "110m", "tdt_ctc", "0.6b"),
    )
    return model.name if model else None


@lru_cache(maxsize=1)
def detect_engines() -> list[EngineFinding]:
    findings: list[EngineFinding] = []
    home = Path.home()

    mac_cli = _which("macparakeet-cli")
    if mac_cli:
        healthy, supports_110m, model_flag, detail = _macparakeet_probe(mac_cli)
        findings.append(
            EngineFinding(
                id="macparakeet-110m",
                name="MacParakeet 110M",
                available=healthy,
                runnable=healthy and supports_110m,
                priority=10,
                detail=detail if supports_110m else f"{detail}; selectable 110M model not confirmed",
                model="parakeet-tdt_ctc-110m",
                test_command=(
                    "macparakeet-cli transcribe <audio-file> --model parakeet-tdt_ctc-110m --format json"
                    if model_flag
                    else "macparakeet-cli transcribe <audio-file> --format json"
                ),
            )
        )
        findings.append(
            EngineFinding(
                id="macparakeet",
                name="MacParakeet",
                available=healthy,
                runnable=healthy,
                priority=35,
                detail="Healthy CLI; configured local Parakeet model will be used",
                test_command="macparakeet-cli transcribe <audio-file> --format json",
            )
        )
    else:
        findings.append(
            EngineFinding(
                id="macparakeet-110m",
                name="MacParakeet 110M",
                available=False,
                runnable=False,
                priority=10,
                detail="CLI not found",
                install_hint="brew install moona3k/tap/macparakeet-cli",
            )
        )

    mlx_cli = _which("parakeet-mlx")
    mlx_module = _module_available("parakeet_mlx")
    for priority, repo, label in (
        (20, PARAKEET_110M, "Parakeet MLX 110M"),
        (40, PARAKEET_06B_V3, "Parakeet MLX 0.6B v3"),
        (45, PARAKEET_06B_V2, "Parakeet MLX 0.6B v2"),
    ):
        cached = _cached_hf_model(repo)
        available = bool(mlx_cli or mlx_module)
        findings.append(
            EngineFinding(
                id="parakeet-mlx-" + repo.rsplit("-", 1)[-1],
                name=label,
                available=available,
                runnable=bool(mlx_cli and cached),
                priority=priority,
                detail=(
                    "CLI and model cache found"
                    if mlx_cli and cached
                    else "Package found; model is not cached"
                    if available
                    else "Package not found"
                ),
                model=repo,
                test_command=(
                    f"parakeet-mlx <audio-file> --model {repo} --output-format txt"
                    if mlx_cli
                    else None
                ),
                install_hint=None if available else "uv tool install parakeet-mlx",
            )
        )

    parakeet_cpp = _which(
        "parakeet-cli",
        source_candidates=(
            home / "parakeet.cpp" / "build" / "examples" / "cli" / "parakeet-cli",
            home / "parakeet.cpp" / "build" / "bin" / "parakeet-cli",
        ),
    )
    cpp_model = _parakeet_cpp_model(parakeet_cpp)
    port_model = cpp_model.name if cpp_model else _parakeet_port_presence()
    findings.append(
        EngineFinding(
            id="parakeet-cpp",
            name="parakeet.cpp",
            available=bool(parakeet_cpp or port_model),
            runnable=bool(parakeet_cpp and cpp_model),
            priority=30 if port_model and ("110m" in port_model.lower() or "tdt_ctc" in port_model.lower()) else 50,
            detail=(
                "CLI and local 110M GGUF found"
                if parakeet_cpp and cpp_model and ("110m" in cpp_model.name.lower() or "tdt_ctc" in cpp_model.name.lower())
                else "CLI and local GGUF found"
                if parakeet_cpp and cpp_model
                else "Local ONNX/GGUF model found; compatible CLI not found"
                if port_model
                else "CLI or local model not found"
            ),
            model=port_model,
            test_command="parakeet-cli transcribe --model <model-file> --input <audio-file> --json",
        )
    )

    whisper_cli = _which(
        "whisper-cli",
        "whisper-cpp",
        source_candidates=(
            home / "whisper.cpp" / "build" / "bin" / "whisper-cli",
            home / "whisper.cpp" / "main",
        ),
    )
    whisper_model = _whisper_model(whisper_cli)
    findings.append(
        EngineFinding(
            id="whisper-cpp",
            name="whisper.cpp",
            available=bool(whisper_cli),
            runnable=bool(whisper_cli and whisper_model),
            priority=70,
            detail=(
                "CLI and local model found"
                if whisper_cli and whisper_model
                else "CLI found; no ggml model found"
                if whisper_cli
                else "CLI not found"
            ),
            model=whisper_model.name if whisper_model else None,
            test_command="whisper-cli -m <model-file> -f <audio-file> -otxt",
            install_hint=None if whisper_cli else "brew install whisper-cpp",
        )
    )

    for priority, module, commands, name, hint in (
        (75, "mlx_whisper", ("mlx_whisper",), "MLX Whisper", "uv tool install mlx-whisper"),
        (80, "whisper", ("whisper",), "OpenAI Whisper", "uv tool install openai-whisper"),
        (85, "faster_whisper", ("faster-whisper", "insanely-fast-whisper"), "Faster Whisper", "uv tool install faster-whisper"),
    ):
        executable = _which(*commands)
        available = bool(executable or _module_available(module))
        findings.append(
            EngineFinding(
                id=module.replace("_", "-"),
                name=name,
                available=available,
                runnable=False,
                priority=priority,
                detail=(
                    "Package/CLI found; no offline cached-model adapter was confirmed"
                    if available
                    else "Package not found"
                ),
                install_hint=None if available else hint,
            )
        )

    lm_roots = (
        home / ".cache" / "lm-studio" / "models",
        home / "Library" / "Application Support" / "LM Studio" / "models",
    )
    lm_whisper = _find_model(lm_roots, suffixes=(".bin", ".gguf", ".onnx"), terms=("whisper",))
    lm_running = _process_present("LM Studio")
    ollama = _which("ollama")
    ollama_list = _run([ollama, "list"], timeout=5) if ollama else None
    ollama_whisper = bool(ollama_list and "whisper" in ollama_list.stdout.lower())
    findings.extend(
        [
            EngineFinding(
                id="lm-studio",
                name="LM Studio",
                available=bool(lm_running or lm_whisper),
                runnable=False,
                priority=200,
                detail=(
                    "Process and whisper-named cache detected; audio endpoint is not assumed"
                    if lm_running and lm_whisper
                    else "Presence detected; audio endpoint is not assumed"
                ),
                informational=True,
            ),
            EngineFinding(
                id="ollama",
                name="Ollama",
                available=bool(ollama),
                runnable=False,
                priority=210,
                detail=(
                    "Whisper-named model listed; community wrappers are not treated as first-class STT"
                    if ollama_whisper
                    else "Presence detected; no first-class STT adapter"
                ),
                informational=True,
            ),
            EngineFinding(
                id="fluidvoice",
                name="FluidVoice",
                available=_process_present("FluidVoice"),
                runnable=False,
                priority=220,
                detail="Process presence only; SafaraKeet never controls FluidVoice",
                informational=True,
            ),
        ]
    )
    return sorted(findings, key=lambda item: item.priority)


def preferred_engine(findings: list[EngineFinding]) -> EngineFinding | None:
    candidates = [item for item in findings if item.runnable and not item.informational]
    return min(candidates, key=lambda item: item.priority, default=None)


def engine_report() -> dict[str, Any]:
    findings = detect_engines()
    selected = preferred_engine(findings)
    return {
        "engines": [item.public() for item in findings],
        "preferred_engine": selected.public() if selected else None,
        "ready": selected is not None,
        "message": f"Using {selected.name}" if selected else "No runnable local STT engine was found",
    }


def _parse_stdout(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    candidates = [value, *reversed(value.splitlines())]
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            for key in ("text", "transcript", "transcription"):
                if isinstance(payload.get(key), str):
                    return payload[key].strip()
    return value


def run_transcription(engine: EngineFinding, audio_path: Path, work_dir: Path) -> str:
    if engine.id.startswith("parakeet-mlx-") and engine.model:
        command = [
            _which("parakeet-mlx") or "parakeet-mlx",
            str(audio_path),
            "--model",
            engine.model,
            "--output-dir",
            str(work_dir),
            "--output-format",
            "txt",
        ]
    elif engine.id in {"macparakeet-110m", "macparakeet"}:
        binary = _which("macparakeet-cli") or "macparakeet-cli"
        command = [binary, "transcribe", str(audio_path), "--format", "json"]
        if engine.id == "macparakeet-110m":
            help_result = _run([binary, "transcribe", "--help"])
            if help_result and "--model" in f"{help_result.stdout}\n{help_result.stderr}":
                command.extend(["--model", "parakeet-tdt_ctc-110m"])
    elif engine.id == "parakeet-cpp":
        binary = _which(
            "parakeet-cli",
            source_candidates=(
                Path.home() / "parakeet.cpp" / "build" / "examples" / "cli" / "parakeet-cli",
                Path.home() / "parakeet.cpp" / "build" / "bin" / "parakeet-cli",
            ),
        )
        model = _parakeet_cpp_model(binary)
        if not binary or not model:
            raise RuntimeError("parakeet.cpp binary or model disappeared after detection")
        command = [binary, "transcribe", "--model", str(model), "--input", str(audio_path), "--json"]
    elif engine.id == "whisper-cpp":
        binary = _which("whisper-cli", "whisper-cpp")
        model = _whisper_model(binary)
        if not binary or not model:
            raise RuntimeError("whisper.cpp binary or model disappeared after detection")
        command = [binary, "-m", str(model), "-f", str(audio_path), "-otxt", "-of", str(work_dir / "transcript")]
    else:
        raise RuntimeError(f"The selected engine adapter is unavailable: {engine.name}")

    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=300, check=False, cwd=work_dir
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Local transcription timed out after five minutes") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown local engine error").strip()
        raise RuntimeError(detail[-1000:])

    outputs = sorted(work_dir.glob("*.txt"), key=lambda path: path.stat().st_mtime, reverse=True)
    text = outputs[0].read_text(encoding="utf-8").strip() if outputs else _parse_stdout(result.stdout)
    if not text:
        raise RuntimeError("The engine completed but returned an empty transcript")
    return text
