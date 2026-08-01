from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .engines import PARAKEET_110M

SAMPLE_RATE = 16_000
MAX_CHUNK_BYTES = SAMPLE_RATE * 4 * 5
STREAM_OPEN_TIMEOUT_SECONDS = 12

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="safarakeet-live")
_model: Any | None = None
session_lock = asyncio.Lock()


def supports_streaming(engine: dict | None) -> bool:
    return bool(engine and str(engine.get("id", "")).startswith("parakeet-mlx-"))


def _load_model():
    global _model
    if _model is None:
        from parakeet_mlx import from_pretrained

        _model = from_pretrained(PARAKEET_110M)
    return _model


async def _inference(function, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, function, *args)


async def warm_model() -> None:
    await _inference(_load_model)


def _open_stream():
    stream = _load_model().transcribe_stream()
    stream.__enter__()
    return stream


async def open_stream():
    try:
        return await asyncio.wait_for(
            _inference(_open_stream), timeout=STREAM_OPEN_TIMEOUT_SECONDS
        )
    except TimeoutError as exc:
        raise RuntimeError(
            "The local live engine is taking too long to start. Try again in a moment."
        ) from exc


def _add_audio(stream, raw: bytes) -> str:
    import mlx.core as mx
    import numpy as np

    audio = np.frombuffer(raw, dtype=np.float32)
    if audio.size:
        stream.add_audio(mx.array(audio))
    return stream.result.text.strip()


async def add_audio(stream, raw: bytes) -> str:
    if len(raw) > MAX_CHUNK_BYTES:
        raise ValueError("Live audio chunk is too large")
    return await _inference(_add_audio, stream, raw)


def _result(stream) -> str:
    return stream.result.text.strip()


async def result(stream) -> str:
    return await _inference(_result, stream)


def _close_stream(stream) -> None:
    stream.__exit__(None, None, None)


async def close_stream(stream) -> None:
    await _inference(_close_stream, stream)
