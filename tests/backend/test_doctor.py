from __future__ import annotations

import json

from app.backend import doctor


def test_doctor_recommends_live_profile_for_ready_apple_silicon(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(doctor.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(doctor.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(doctor, "_memory_bytes", lambda system: 16 * 1024**3)
    monkeypatch.setattr(doctor, "_model_cached", lambda: True)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"tool-{name}")
    monkeypatch.setattr(
        doctor.shutil,
        "disk_usage",
        lambda path: doctor.shutil._ntuple_diskusage(20 * 1024**3, 1, 19 * 1024**3),
    )

    report = doctor.capability_report()

    assert report["recommended_profile"] == "live-mlx"
    assert report["setup_ready"] is True
    assert report["live_ready_after_setup"] is True
    assert report["privacy"] == "scrubbed"


def test_doctor_json_shape_contains_no_machine_identifiers(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(doctor.platform, "system", lambda: "Other")
    monkeypatch.setattr(doctor.platform, "machine", lambda: "unknown")
    monkeypatch.setattr(doctor, "_memory_bytes", lambda system: None)
    monkeypatch.setattr(doctor, "_model_cached", lambda: False)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)

    encoded = json.dumps(doctor.capability_report(), sort_keys=True)

    assert "/" not in encoded
    assert "\\" not in encoded
    assert "@" not in encoded
    assert json.loads(encoded)["recommended_profile"] == "unsupported"


def test_connection_report_returns_ephemeral_verified_private_url(monkeypatch):
    monkeypatch.setattr(doctor, "_local_app_ready", lambda port: port == 8765)

    def tailscale(arguments):
        if arguments[:1] == ["status"]:
            return {"BackendState": "Running"}
        return {
            "TCP": {"8443": {"HTTPS": True}},
            "Web": {
                "<private-host>:8443": {
                    "Handlers": {"/": {"Proxy": "http://localhost:8765"}}
                }
            },
        }

    monkeypatch.setattr(doctor, "_tailscale_json", tailscale)

    assert doctor.connection_report(8765, 8443) == {
        "state": "ready",
        "private_https_url": "https://<private-host>:8443/",
    }


def test_connection_report_does_not_accept_wrong_serve_target(monkeypatch):
    monkeypatch.setattr(doctor, "_local_app_ready", lambda port: True)

    def tailscale(arguments):
        if arguments[:1] == ["status"]:
            return {"BackendState": "Running"}
        return {
            "TCP": {"8443": {"HTTPS": True}},
            "Web": {
                "<private-host>:8443": {
                    "Handlers": {"/": {"Proxy": "http://localhost:9999"}}
                }
            },
        }

    monkeypatch.setattr(doctor, "_tailscale_json", tailscale)

    assert doctor.connection_report(8765, 8443) == {"state": "serve-not-configured"}


def test_connection_report_is_scrubbed_until_share_is_ready(monkeypatch):
    monkeypatch.setattr(doctor, "_local_app_ready", lambda port: True)
    monkeypatch.setattr(doctor, "_tailscale_json", lambda arguments: None)

    report = doctor.connection_report(8765, 8443)

    assert report == {"state": "tailscale-unavailable"}
    assert "private_https_url" not in json.dumps(doctor.capability_report(), sort_keys=True)
