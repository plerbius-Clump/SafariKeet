from fastapi.testclient import TestClient

from app.backend.engines import EngineFinding
from app.backend.store import Store
import app.backend.main as main


def test_connection_report_is_not_cached(monkeypatch):
    monkeypatch.setattr(
        main,
        "connection_report",
        lambda: {"state": "ready", "private_https_url": "https://<private-host>:8443/"},
    )

    response = TestClient(main.app).get("/api/connection")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["state"] == "ready"


def test_transcribe_persists_mocked_local_result(tmp_path, monkeypatch):
    engine = EngineFinding(
        id="test-engine",
        name="Test engine",
        available=True,
        runnable=True,
        priority=1,
        detail="synthetic adapter",
    )
    monkeypatch.setattr(main, "store", Store(tmp_path / "history.sqlite3"))
    monkeypatch.setattr(main, "engine_report", lambda: {"preferred_engine": engine.public(), "engines": []})
    monkeypatch.setattr(main, "preferred_engine_from_report", lambda report: engine)
    monkeypatch.setattr(main, "_to_wav", lambda source, target: source)
    monkeypatch.setattr(main, "run_transcription", lambda selected, source, work: "Private synthetic transcript.")

    client = TestClient(main.app)
    response = client.post(
        "/api/transcribe",
        files={"audio": ("sample.webm", b"synthetic-audio", "audio/webm")},
        data={"duration_ms": "2400"},
    )

    assert response.status_code == 200
    transcript = response.json()["transcript"]
    assert transcript["text"] == "Private synthetic transcript."
    assert client.get("/api/history").json()["items"][0]["id"] == transcript["id"]


def test_live_transcription_streams_and_persists_block(tmp_path, monkeypatch):
    engine = EngineFinding(
        id="parakeet-mlx-110m",
        name="Parakeet MLX 110M",
        available=True,
        runnable=True,
        priority=1,
        detail="synthetic streaming adapter",
        model="synthetic/live-model",
        live_capable=True,
    )
    stream = object()

    async def open_stream(selected):
        assert selected["model"] == "synthetic/live-model"
        return stream

    async def add_audio(selected_stream, raw):
        assert selected_stream is stream
        assert raw == b"synthetic-pcm"
        return "Private synthetic"

    async def result(selected_stream):
        assert selected_stream is stream
        return "Private synthetic transcript."

    async def close_stream(selected_stream):
        assert selected_stream is stream

    monkeypatch.setattr(main, "store", Store(tmp_path / "history.sqlite3"))
    monkeypatch.setattr(
        main,
        "engine_report",
        lambda: {"preferred_engine": engine.public(), "preferred_live_engine": engine.public(), "engines": []},
    )
    monkeypatch.setattr(main.live, "open_stream", open_stream)
    monkeypatch.setattr(main.live, "add_audio", add_audio)
    monkeypatch.setattr(main.live, "result", result)
    monkeypatch.setattr(main.live, "close_stream", close_stream)

    client = TestClient(main.app)
    with client.websocket_connect("/api/live") as websocket:
        assert websocket.receive_json() == {"type": "status", "status": "warming"}
        assert websocket.receive_json() == {"type": "status", "status": "ready"}
        websocket.send_bytes(b"synthetic-pcm")
        assert websocket.receive_json() == {
            "type": "partial",
            "text": "Private synthetic",
        }
        websocket.send_json({"type": "finalize", "duration_ms": 2400})
        final = websocket.receive_json()

    assert final["type"] == "final"
    assert final["transcript"]["text"] == "Private synthetic transcript."
    assert final["transcript"]["duration_ms"] == 2400
    assert client.get("/api/history").json()["items"][0]["id"] == final["transcript"]["id"]


def test_live_transcription_reports_stream_startup_error(monkeypatch):
    engine = EngineFinding(
        id="parakeet-mlx-110m",
        name="Parakeet MLX 110M",
        available=True,
        runnable=True,
        priority=1,
        detail="synthetic streaming adapter",
        model="synthetic/live-model",
        live_capable=True,
    )

    async def open_stream(selected):
        assert selected["model"] == "synthetic/live-model"
        raise RuntimeError("Synthetic live engine startup failure.")

    monkeypatch.setattr(
        main,
        "engine_report",
        lambda: {"preferred_engine": engine.public(), "preferred_live_engine": engine.public(), "engines": []},
    )
    monkeypatch.setattr(main.live, "open_stream", open_stream)

    with TestClient(main.app).websocket_connect("/api/live") as websocket:
        assert websocket.receive_json() == {"type": "status", "status": "warming"}
        assert websocket.receive_json() == {
            "type": "error",
            "message": "Synthetic live engine startup failure.",
        }


def test_history_archives_and_restores_transcript(tmp_path, monkeypatch):
    store = Store(tmp_path / "history.sqlite3")
    transcript = store.add_transcript("Synthetic archived test.", 1250, "Test engine")
    monkeypatch.setattr(main, "store", store)
    client = TestClient(main.app)

    response = client.patch(f"/api/history/{transcript['id']}", json={"archived": True})

    assert response.status_code == 200
    assert response.json() == {"archived": True}
    assert client.get("/api/history").json() == {"items": [], "total": 0, "limit": 25, "offset": 0}
    assert client.get("/api/history?archived=true").json()["items"] == [
        {**transcript, "archived": True}
    ]

    response = client.patch(f"/api/history/{transcript['id']}", json={"archived": False})

    assert response.status_code == 200
    assert client.get("/api/history").json()["items"] == [transcript]
    assert client.patch("/api/history/missing", json={"archived": True}).status_code == 404


def test_history_bulk_archive_restore_and_delete(tmp_path, monkeypatch):
    store = Store(tmp_path / "history.sqlite3")
    first = store.add_transcript("First synthetic batch.", 1000, "Test engine")
    second = store.add_transcript("Second synthetic batch.", 2000, "Test engine")
    third = store.add_transcript("Third synthetic batch.", 3000, "Test engine")
    monkeypatch.setattr(main, "store", store)
    client = TestClient(main.app)

    archived = client.patch(
        "/api/history/bulk",
        json={"ids": [first["id"], second["id"], first["id"]], "archived": True},
    )

    assert archived.status_code == 200
    assert set(archived.json()["updated_ids"]) == {first["id"], second["id"]}
    assert client.get("/api/history").json()["items"] == [third]

    restored = client.patch(
        "/api/history/bulk",
        json={"ids": [first["id"], second["id"]], "archived": False},
    )
    assert set(restored.json()["updated_ids"]) == {first["id"], second["id"]}

    deleted = client.request("DELETE", "/api/history/bulk", json={"ids": [second["id"], "missing"]})
    assert deleted.status_code == 200
    assert deleted.json() == {"deleted_ids": [second["id"]]}
    assert {item["id"] for item in store.list_transcripts()} == {first["id"], third["id"]}


def test_history_pagination_reports_total_and_bulk_archive_moves_selected_page(tmp_path, monkeypatch):
    store = Store(tmp_path / "history.sqlite3")
    transcripts = [store.add_transcript(f"Synthetic page {index}.", 1000, "Test engine") for index in range(12)]
    monkeypatch.setattr(main, "store", store)
    client = TestClient(main.app)

    first_page = client.get("/api/history?limit=10&offset=0").json()
    assert first_page["total"] == 12
    assert len(first_page["items"]) == 10
    assert first_page["limit"] == 10
    second_page = client.get("/api/history?limit=10&offset=10").json()
    assert second_page["total"] == 12
    assert len(second_page["items"]) == 2

    selected = [item["id"] for item in first_page["items"]]
    response = client.patch("/api/history/bulk", json={"ids": selected, "archived": True})
    assert response.status_code == 200
    assert set(response.json()["updated_ids"]) == set(selected)
    assert client.get("/api/history?limit=10").json()["total"] == 2
    archived = client.get("/api/history?archived=true&limit=10").json()
    assert archived["total"] == 10
    assert {item["id"] for item in archived["items"]} == set(selected)


def test_history_bulk_limits_selection_size(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "store", Store(tmp_path / "history.sqlite3"))
    response = TestClient(main.app).patch(
        "/api/history/bulk",
        json={"ids": [f"synthetic-{index}" for index in range(101)], "archived": True},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Choose at most 100 transcripts"


def test_history_text_update_persists_trimmed_text(tmp_path, monkeypatch):
    store = Store(tmp_path / "history.sqlite3")
    transcript = store.add_transcript("Original synthetic text.", 1250, "Test engine")
    monkeypatch.setattr(main, "store", store)

    response = TestClient(main.app).patch(
        f"/api/history/{transcript['id']}/text",
        json={"text": "  Edited synthetic text.  "},
    )

    assert response.status_code == 200
    assert response.json() == {"transcript": {**transcript, "text": "Edited synthetic text."}}
    assert store.list_transcripts() == [{**transcript, "text": "Edited synthetic text."}]


def test_history_text_update_rejects_blank_or_missing_transcript(tmp_path, monkeypatch):
    store = Store(tmp_path / "history.sqlite3")
    transcript = store.add_transcript("Original synthetic text.", 1250, "Test engine")
    monkeypatch.setattr(main, "store", store)
    client = TestClient(main.app)

    blank = client.patch(f"/api/history/{transcript['id']}/text", json={"text": " \n "})
    missing = client.patch("/api/history/missing/text", json={"text": "Synthetic text."})

    assert blank.status_code == 422
    assert blank.json()["detail"] == "Transcript text cannot be empty"
    assert missing.status_code == 404
