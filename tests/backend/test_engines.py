from dataclasses import replace

import sys

from app.backend.engines import EngineFinding, _which, preferred_engine, preferred_live_engine, select_engine


def finding(name: str, priority: int, runnable: bool = True) -> EngineFinding:
    return EngineFinding(
        id=name.lower(),
        name=name,
        available=runnable,
        runnable=runnable,
        priority=priority,
        detail="synthetic finding",
    )


def test_preferred_engine_uses_priority_order():
    selected = preferred_engine([finding("Whisper", 70), finding("Parakeet", 20)])
    assert selected is not None
    assert selected.name == "Parakeet"


def test_preferred_engine_skips_unrunnable_and_informational():
    info = finding("Presence only", 1)
    info = replace(info, informational=True)
    selected = preferred_engine([info, finding("Missing", 2, False), finding("Ready", 3)])
    assert selected is not None
    assert selected.name == "Ready"


def test_live_selection_is_independent_of_batch_selection():
    batch = finding("Batch", 1)
    live = replace(finding("Live", 20, False), live_capable=True, model="synthetic/model")

    assert preferred_engine([batch, live]) == batch
    assert preferred_live_engine([batch, live]) == live


def test_explicit_engine_selection_requires_live_support_when_requested():
    batch = finding("Batch", 1)
    live = replace(finding("Live", 20), live_capable=True, model="synthetic/model")

    assert select_engine([batch, live], "live", require_live=True) == live
    assert select_engine([batch, live], "batch", require_live=True) is None
    assert select_engine([batch, live], "missing") is None


def test_which_finds_virtual_environment_sibling(monkeypatch, tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    interpreter = bin_dir / "python"
    executable = bin_dir / "synthetic-engine"
    interpreter.touch(mode=0o755)
    executable.touch(mode=0o755)
    monkeypatch.setattr(sys, "executable", str(interpreter))
    monkeypatch.setattr("app.backend.engines.shutil.which", lambda _: None)

    assert _which("synthetic-engine") == str(executable)
