import sqlite3

from app.backend.store import Store


def test_transcript_lifecycle(tmp_path):
    store = Store(tmp_path / "history.sqlite3")
    created = store.add_transcript("Synthetic local test.", 1250, "Test engine")

    assert store.list_transcripts() == [created]
    assert store.delete_transcript(created["id"]) is True
    assert store.list_transcripts() == []


def test_transcript_archive_filters_and_restores(tmp_path):
    store = Store(tmp_path / "history.sqlite3")
    active = store.add_transcript("Active synthetic test.", 1250, "Test engine")
    archived = store.add_transcript("Archived synthetic test.", 1250, "Test engine")

    assert store.archive_transcript(archived["id"]) is True
    assert store.list_transcripts() == [active]
    assert store.list_transcripts(archived=True) == [{**archived, "archived": True}]

    assert store.archive_transcript(archived["id"], archived=False) is True
    assert {item["id"] for item in store.list_transcripts()} == {active["id"], archived["id"]}
    assert store.archive_transcript("missing") is False


def test_transcript_text_update_trims_and_persists(tmp_path):
    store = Store(tmp_path / "history.sqlite3")
    created = store.add_transcript("Original synthetic text.", 1250, "Test engine")

    updated = store.update_transcript_text(created["id"], "  Edited synthetic text.  ")

    assert updated == {**created, "text": "Edited synthetic text."}
    assert store.list_transcripts() == [updated]
    assert store.update_transcript_text("missing", "Synthetic text.") is None


def test_transcript_text_update_rejects_blank_text(tmp_path):
    store = Store(tmp_path / "history.sqlite3")
    created = store.add_transcript("Original synthetic text.", 1250, "Test engine")

    try:
        store.update_transcript_text(created["id"], " \n\t ")
    except ValueError as error:
        assert str(error) == "Transcript text cannot be empty"
    else:
        raise AssertionError("Expected blank transcript text to be rejected")


def test_transcript_archive_migrates_existing_database(tmp_path):
    path = tmp_path / "history.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE transcripts (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                engine TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO transcripts VALUES (?, ?, ?, ?, ?)",
            ("legacy", "Legacy synthetic test.", "2026-01-01T00:00:00+00:00", 1000, "Test engine"),
        )

    store = Store(path)

    assert store.list_transcripts() == [
        {
            "id": "legacy",
            "text": "Legacy synthetic test.",
            "created_at": "2026-01-01T00:00:00+00:00",
            "duration_ms": 1000,
            "engine": "Test engine",
            "archived": False,
        }
    ]


def test_settings_default_and_update(tmp_path):
    store = Store(tmp_path / "history.sqlite3")

    assert store.settings() == {"theme": "dark", "skin": "graphite", "https_only": False, "history_page_size": 25, "speech_engine_id": "automatic"}
    assert store.update_settings({"theme": "system"}) == {
        "theme": "system",
        "skin": "graphite",
        "https_only": False,
        "history_page_size": 25,
        "speech_engine_id": "automatic",
    }
