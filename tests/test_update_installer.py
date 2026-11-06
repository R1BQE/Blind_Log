import hashlib
import os
import struct
import threading

import requests

from services import update_installer


def make_fake_pe():
    """Return a minimal byte sequence with valid DOS and PE signatures."""
    data = bytearray(256)
    data[:2] = b"MZ"
    data[0x3C:0x40] = struct.pack("<I", 0x40)
    data[0x40:0x44] = b"PE\\x00\\x00"
    return bytes(data)


class FakeResponse:
    def __init__(self, payload, content_length=True):
        self.payload = payload
        self.headers = {"content-length": str(len(payload))} if content_length else {}
        self.closed = False

    def raise_for_status(self):
        return None

    def iter_content(self, chunk_size):
        for offset in range(0, len(self.payload), chunk_size):
            yield self.payload[offset:offset + chunk_size]

    def close(self):
        self.closed = True


def prepare_worker(monkeypatch, tmp_path, payload, content_length=True):
    response = FakeResponse(payload, content_length=content_length)
    launched = []
    monkeypatch.setattr(update_installer, "_get_update_root", lambda: str(tmp_path / "staging"))
    monkeypatch.setattr(update_installer, "get_app_path", lambda: str(tmp_path / "app"))
    monkeypatch.setattr(update_installer.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(
        update_installer, "create_update_ps1",
        lambda exe, pid, app_dir, work_dir, confirmation_file, token: str(tmp_path / "installer.ps1")
    )
    monkeypatch.setattr(
        update_installer.subprocess, "Popen",
        lambda args, **kwargs: launched.append((args, kwargs))
    )
    os.makedirs(tmp_path / "app", exist_ok=True)
    return response, launched


def test_valid_windows_executable_is_recognized(tmp_path):
    path = tmp_path / "Blind_log.exe"
    path.write_bytes(make_fake_pe())
    assert update_installer._valid_windows_executable(str(path))


def test_invalid_file_is_not_recognized_as_executable(tmp_path):
    path = tmp_path / "Blind_log.exe"
    path.write_bytes(b"not an executable")
    assert not update_installer._valid_windows_executable(str(path))


def test_worker_downloads_and_starts_installer(monkeypatch, tmp_path):
    payload = make_fake_pe()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload)
    digest = hashlib.sha256(payload).hexdigest()

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None, expected_sha256=digest
    )

    assert result.success
    assert result.data["installer_started"] is True
    assert launched
    assert response.closed


def test_worker_downloads_without_content_length(monkeypatch, tmp_path):
    payload = make_fake_pe()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload, content_length=False)

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None,
        expected_sha256=hashlib.sha256(payload).hexdigest()
    )

    assert result.success
    assert launched
    assert response.closed


def test_worker_reports_progress(monkeypatch, tmp_path):
    payload = make_fake_pe()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload)
    progress = []

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None,
        lambda percent, message: progress.append((percent, message)),
        expected_sha256=hashlib.sha256(payload).hexdigest()
    )

    assert result.success
    assert launched
    assert progress
    assert progress[-1][0] <= 99
    assert response.closed


def test_worker_rejects_checksum_mismatch(monkeypatch, tmp_path):
    payload = make_fake_pe()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload)

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None, expected_sha256="0" * 64
    )

    assert not result.success
    assert "checksum mismatch" in result.error.lower()
    assert not launched
    assert response.closed


def test_worker_rejects_non_executable_file(monkeypatch, tmp_path):
    payload = b"not a PE executable"
    response, launched = prepare_worker(monkeypatch, tmp_path, payload)

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None,
        expected_sha256=hashlib.sha256(payload).hexdigest()
    )

    assert not result.success
    assert "valid windows executable" in result.error.lower()
    assert not launched
    assert response.closed


def test_worker_rejects_truncated_download(monkeypatch, tmp_path):
    payload = make_fake_pe()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload + b"extra")
    response.headers["content-length"] = str(len(payload) + 100)

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None,
        expected_sha256=hashlib.sha256(payload).hexdigest()
    )

    assert not result.success
    assert "size mismatch" in result.error.lower()
    assert not launched
    assert response.closed


def test_worker_handles_http_error(monkeypatch, tmp_path):
    monkeypatch.setattr(update_installer, "_get_update_root", lambda: str(tmp_path / "staging"))
    monkeypatch.setattr(
        update_installer.requests, "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.HTTPError("404 Not Found"))
    )

    result = update_installer._download_and_update_worker(
        "https://example.test/missing.exe", None, expected_sha256="0" * 64
    )

    assert not result.success
    assert "404" in result.error


def test_worker_handles_unexpected_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(update_installer, "_get_update_root", lambda: str(tmp_path / "staging"))
    monkeypatch.setattr(
        update_installer.requests, "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unexpected failure"))
    )

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None, expected_sha256="0" * 64
    )

    assert not result.success
    assert "unexpected failure" in result.error


def test_worker_stops_when_cancelled(monkeypatch, tmp_path):
    payload = make_fake_pe()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload)
    cancel_event = threading.Event()
    cancel_event.set()

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None,
        cancel_event=cancel_event,
        expected_sha256=hashlib.sha256(payload).hexdigest()
    )

    assert not result.success
    assert "cancelled" in result.error.lower()
    assert not launched
    assert response.closed


def test_worker_requires_checksum(monkeypatch, tmp_path):
    payload = make_fake_pe()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload)

    result = update_installer._download_and_update_worker(
        "https://example.test/Blind_log.exe", None
    )

    assert not result.success
    assert "sha-256" in result.error.lower()
    assert not launched
    assert response is None or response.closed


def test_generated_installer_waits_for_startup_confirmation_and_keeps_backup(tmp_path):
    new_exe = tmp_path / "Blind_log.exe"
    new_exe.write_bytes(make_fake_pe())
    work_dir = tmp_path / "update-work"
    work_dir.mkdir()
    confirmation = work_dir / "startup-confirmation.txt"
    token = "test-token"

    script_path = update_installer.create_update_ps1(
        str(new_exe), 1234, str(tmp_path / "app"), str(work_dir),
        str(confirmation), token
    )
    script = open(script_path, encoding="utf-8-sig").read()

    assert "WaitForExit(90000)" in script
    assert "startup-confirmation.txt" in script
    assert "New version confirmed successful initialization." in script
    assert "The new version did not confirm startup within 60 seconds." in script
    assert "Blind_log.exe.bak" in script
    assert "Previous executable restored." in script
