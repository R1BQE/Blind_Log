import io
import os
import zipfile

import threading
import requests

from services import update_installer


def make_update_zip():
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("Blind_log.exe", b"new executable")
    return stream.getvalue()


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

    monkeypatch.setattr(update_installer, "_get_update_temp_root", lambda: str(tmp_path / "staging"))
    monkeypatch.setattr(update_installer, "get_app_path", lambda: str(tmp_path / "app"))
    monkeypatch.setattr(update_installer.requests, "get", lambda *args, **kwargs: response)
    monkeypatch.setattr(
        update_installer, "create_update_ps1",
        lambda extracted, pid, app_dir, work_dir: str(tmp_path / "fake-installer.ps1")
    )
    monkeypatch.setattr(
        update_installer.subprocess, "Popen",
        lambda args, **kwargs: launched.append((args, kwargs))
    )
    os.makedirs(tmp_path / "app", exist_ok=True)
    return response, launched


def test_extract_zip_accepts_valid_update(tmp_path):
    archive_path = tmp_path / "update.zip"
    archive_path.write_bytes(make_update_zip())

    assert update_installer.extract_zip(str(archive_path), str(tmp_path / "extract"))
    assert (tmp_path / "extract" / "Blind_log.exe").read_bytes() == b"new executable"


def test_extract_zip_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")

    assert not update_installer.extract_zip(str(archive_path), str(tmp_path / "extract"))
    assert not (tmp_path / "outside.txt").exists()


def test_extract_zip_rejects_archive_without_application(tmp_path):
    archive_path = tmp_path / "wrong.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("readme.txt", "not the application")

    assert not update_installer.extract_zip(str(archive_path), str(tmp_path / "extract"))


def test_worker_downloads_without_content_length(monkeypatch, tmp_path):
    response, launched = prepare_worker(
        monkeypatch, tmp_path, make_update_zip(), content_length=False
    )

    result = update_installer._download_and_update_worker("https://example.test/update.zip", None)

    assert result.success
    assert result.data["installer_started"] is True
    assert launched
    assert response.closed


def test_worker_reports_progress_when_content_length_is_available(monkeypatch, tmp_path):
    payload = make_update_zip()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload)
    progress = []

    result = update_installer._download_and_update_worker(
        "https://example.test/update.zip",
        None,
        lambda percent, message: progress.append((percent, message)),
    )

    assert result.success
    assert launched
    assert progress
    assert progress[-1][0] <= 99
    assert response.closed


def test_worker_rejects_truncated_download(monkeypatch, tmp_path):
    payload = make_update_zip()
    response, launched = prepare_worker(monkeypatch, tmp_path, payload + b"extra")
    response.headers["content-length"] = str(len(payload) + 100)

    result = update_installer._download_and_update_worker("https://example.test/update.zip", None)

    assert not result.success
    assert "size mismatch" in result.error.lower()
    assert not launched
    assert response.closed


def test_worker_rejects_corrupt_archive(monkeypatch, tmp_path):
    response, launched = prepare_worker(monkeypatch, tmp_path, b"not a zip archive")

    result = update_installer._download_and_update_worker("https://example.test/update.zip", None)

    assert not result.success
    assert not launched
    assert response.closed


def test_worker_handles_unexpected_exception(monkeypatch, tmp_path):
    monkeypatch.setattr(update_installer, "_get_update_temp_root", lambda: str(tmp_path / "staging"))
    monkeypatch.setattr(
        update_installer.requests, "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("unexpected failure"))
    )

    result = update_installer._download_and_update_worker("https://example.test/update.zip", None)

    assert not result.success
    assert "unexpected failure" in result.error



def test_worker_reports_http_error(monkeypatch, tmp_path):
    monkeypatch.setattr(update_installer, "_get_update_temp_root", lambda: str(tmp_path / "staging"))
    monkeypatch.setattr(
        update_installer.requests, "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(requests.HTTPError("404 Not Found"))
    )

    result = update_installer._download_and_update_worker("https://example.test/missing.zip", None)

    assert not result.success
    assert "404" in result.error


def test_worker_stops_when_cancelled(monkeypatch, tmp_path):
    response, launched = prepare_worker(monkeypatch, tmp_path, make_update_zip())
    cancel_event = threading.Event()
    cancel_event.set()

    result = update_installer._download_and_update_worker(
        "https://example.test/update.zip", None, cancel_event=cancel_event
    )

    assert not result.success
    assert "cancelled" in result.error.lower()
    assert not launched
    assert response.closed
