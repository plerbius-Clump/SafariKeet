from __future__ import annotations

from contextlib import asynccontextmanager
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import live
from .config import MAX_AUDIO_BYTES, database_path
from .doctor import connection_report
from .engines import engine_report, preferred_engine, run_transcription
from .store import Store


@asynccontextmanager
async def lifespan(_: FastAPI):
    report = engine_report()
    if live.supports_streaming(report.get("preferred_engine")):
        try:
            await live.warm_model()
        except Exception:
            pass
    yield


app = FastAPI(
    title="SafaraKeet",
    version="0.1.0",
    docs_url="/api/docs",
    lifespan=lifespan,
)
store = Store(database_path())


class SettingsPatch(BaseModel):
    theme: Literal["dark", "light", "system"] | None = None
    skin: Literal["pickle", "graphite", "frost"] | None = None
    https_only: bool | None = None
    history_page_size: Literal[10, 25, 50] | None = None


class ArchivePatch(BaseModel):
    archived: bool


class TranscriptTextPatch(BaseModel):
    text: str


class BulkTranscriptPatch(BaseModel):
    ids: list[str]
    archived: bool | None = None


def _audio_suffix(content_type: str | None) -> str:
    value = (content_type or "").lower()
    if "mp4" in value or "aac" in value:
        return ".m4a"
    if "ogg" in value:
        return ".ogg"
    if "wav" in value:
        return ".wav"
    return ".webm"


async def _save_limited(upload: UploadFile, target: Path) -> int:
    total = 0
    with target.open("wb") as output:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_AUDIO_BYTES:
                raise HTTPException(status_code=413, detail="Recording exceeds the 40 MB limit")
            output.write(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail="The recording was empty")
    return total


def _to_wav(source: Path, target: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if source.suffix == ".wav":
        return source
    if not ffmpeg:
        raise HTTPException(
            status_code=503,
            detail="This browser audio container needs ffmpeg. Install it with: brew install ffmpeg",
        )
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-ac",
        "1",
        "-ar",
        "16000",
        str(target),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=400, detail="Safari audio could not be decoded")
    return target


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "local_only": True, **engine_report()}


@app.get("/api/connection")
def connection(response: Response) -> dict:
    # The private URL is discovered only for this response. Do not let browsers
    # or intermediary caches retain it.
    response.headers["Cache-Control"] = "no-store"
    return connection_report()


@app.get("/api/history")
def history(limit: int = 25, offset: int = 0, archived: bool = False) -> dict:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(0, offset)
    return {
        "items": store.list_transcripts_page(safe_limit, safe_offset, archived=archived),
        "total": store.count_transcripts(archived=archived),
        "limit": safe_limit,
        "offset": safe_offset,
    }


@app.delete("/api/history")
def clear_history() -> dict:
    return {"deleted": store.clear_transcripts()}


@app.patch("/api/history/bulk")
def archive_history_bulk(patch: BulkTranscriptPatch) -> dict:
    if patch.archived is None:
        raise HTTPException(status_code=422, detail="An archive state is required")
    if len(patch.ids) > 100:
        raise HTTPException(status_code=422, detail="Choose at most 100 transcripts")
    return {"updated_ids": store.archive_transcripts(patch.ids, patch.archived), "archived": patch.archived}


@app.delete("/api/history/bulk")
def delete_history_bulk(patch: BulkTranscriptPatch) -> dict:
    if len(patch.ids) > 100:
        raise HTTPException(status_code=422, detail="Choose at most 100 transcripts")
    return {"deleted_ids": store.delete_transcripts(patch.ids)}


@app.delete("/api/history/{transcript_id}")
def delete_history(transcript_id: str) -> dict:
    if not store.delete_transcript(transcript_id):
        raise HTTPException(status_code=404, detail="Transcript not found")
    return {"deleted": True}


@app.patch("/api/history/{transcript_id}")
def archive_history(transcript_id: str, patch: ArchivePatch) -> dict:
    if not store.archive_transcript(transcript_id, patch.archived):
        raise HTTPException(status_code=404, detail="Transcript not found")
    return {"archived": patch.archived}


@app.patch("/api/history/{transcript_id}/text")
def update_history_text(transcript_id: str, patch: TranscriptTextPatch) -> dict:
    try:
        transcript = store.update_transcript_text(transcript_id, patch.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if transcript is None:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return {"transcript": transcript}


@app.get("/api/settings")
def get_settings() -> dict:
    return store.settings()


@app.patch("/api/settings")
def update_settings(patch: SettingsPatch) -> dict:
    return store.update_settings(patch.model_dump(exclude_none=True))


@app.post("/api/transcribe")
async def transcribe(
    audio: Annotated[UploadFile, File()],
    duration_ms: Annotated[int, Form()] = 0,
) -> dict:
    report = engine_report()
    engine = preferred_engine_from_report(report)
    if engine is None:
        hints = [item["install_hint"] for item in report["engines"] if item.get("install_hint")]
        raise HTTPException(
            status_code=503,
            detail="No runnable local STT engine was found. " + (hints[0] if hints else "Check /api/health."),
        )

    with tempfile.TemporaryDirectory(prefix="safarikeet-") as temporary:
        work_dir = Path(temporary)
        source = work_dir / ("recording" + _audio_suffix(audio.content_type))
        await _save_limited(audio, source)
        wav = _to_wav(source, work_dir / "recording.wav")
        try:
            text = run_transcription(engine, wav, work_dir)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    item = store.add_transcript(text, duration_ms, engine.name)
    return {"transcript": item}


@app.websocket("/api/live")
async def live_transcribe(websocket: WebSocket) -> None:
    await websocket.accept()
    report = engine_report()
    selected = report.get("preferred_engine")
    if not live.supports_streaming(selected):
        await websocket.send_json(
            {
                "type": "error",
                "message": "The selected local engine does not support live transcription.",
            }
        )
        await websocket.close(code=1011)
        return

    stream = None
    try:
        async with live.session_lock:
            await websocket.send_json({"type": "status", "status": "warming"})
            stream = await live.open_stream()
            await websocket.send_json({"type": "status", "status": "ready"})

            while True:
                message = await websocket.receive()
                if audio := message.get("bytes"):
                    text = await live.add_audio(stream, audio)
                    await websocket.send_json({"type": "partial", "text": text})
                    continue

                raw = message.get("text")
                if not raw:
                    continue
                try:
                    control = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if control.get("type") != "finalize":
                    continue

                text = await live.result(stream)
                if not text:
                    await websocket.send_json(
                        {"type": "error", "message": "No speech was detected in this block."}
                    )
                    return
                duration_ms = max(0, int(control.get("duration_ms", 0)))
                transcript = store.add_transcript(text, duration_ms, selected["name"])
                await websocket.send_json({"type": "final", "transcript": transcript})
                return
    except WebSocketDisconnect:
        return
    except (RuntimeError, ValueError) as exc:
        # Stream startup used to close the socket silently, leaving a granted
        # microphone looking like it was still warming in the browser.
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except (RuntimeError, WebSocketDisconnect):
            pass
    finally:
        if stream is not None:
            await live.close_stream(stream)


def preferred_engine_from_report(report: dict):
    selected = report.get("preferred_engine")
    if not selected:
        return None
    # Re-detect into the dataclass used by the adapter. Detection is cheap and avoids
    # making subprocess execution depend on untrusted request data.
    from .engines import detect_engines

    return preferred_engine(detect_engines())


FRONTEND_DIST = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        candidate = (FRONTEND_DIST / path).resolve()
        if path and candidate.is_file() and FRONTEND_DIST.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
