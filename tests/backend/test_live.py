import asyncio

import pytest

from app.backend import live


@pytest.mark.asyncio
async def test_open_stream_times_out_with_actionable_error(monkeypatch):
    async def blocked_inference(*_args):
        await asyncio.Event().wait()

    monkeypatch.setattr(live, "_inference", blocked_inference)
    monkeypatch.setattr(live, "STREAM_OPEN_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(RuntimeError, match="taking too long to start"):
        await live.open_stream({"model": "synthetic/model"})


@pytest.mark.asyncio
async def test_open_stream_uses_selected_model(monkeypatch):
    selected_models = []

    async def capture_inference(function, *args):
        selected_models.append(args[0])
        return object()

    monkeypatch.setattr(live, "_inference", capture_inference)

    await live.open_stream({"model": "synthetic/large-model"})

    assert selected_models == ["synthetic/large-model"]
