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
        await live.open_stream()
