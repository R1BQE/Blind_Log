import pytest

from services.updater import perform_update_check


class DummyResponse:
    def __init__(self, data, text=""):
        self._data = data
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_perform_update_check_returns_result_for_no_update(monkeypatch):
    monkeypatch.setattr('services.updater.get_version', lambda: '1.0.0')
    monkeypatch.setattr(
        'services.updater.requests.get',
        lambda *args, **kwargs: DummyResponse({
            'tag_name': '1.0.0',
            'body': 'No changes',
            'assets': [
                {'name': 'Blind_log.exe', 'browser_download_url': 'https://example.com/Blind_log.exe', 'digest': 'sha256:' + 'a' * 64}
            ]
        })
    )

    result = perform_update_check()

    assert result.success
    assert result.data['update_available'] is False
    assert result.data['current_version'] == '1.0.0'


def test_perform_update_check_returns_update_available(monkeypatch):
    monkeypatch.setattr('services.updater.get_version', lambda: '1.0.0')
    monkeypatch.setattr(
        'services.updater.requests.get',
        lambda *args, **kwargs: DummyResponse({
            'tag_name': '1.0.1',
            'body': 'Minor fixes',
            'assets': [
                {'name': 'Blind_log.exe', 'browser_download_url': 'https://example.com/Blind_log.exe', 'digest': 'sha256:' + 'a' * 64}
            ]
        })
    )

    result = perform_update_check()

    assert result.success
    assert result.data['update_available'] is True
    assert result.data['latest_version'] == '1.0.1'
    assert result.data['download_url'] == 'https://example.com/Blind_log.exe'
    assert result.data['expected_sha256'] == 'a' * 64


def test_perform_update_check_rejects_executable_without_digest(monkeypatch):
    monkeypatch.setattr('services.updater.get_version', lambda: '1.0.0')
    monkeypatch.setattr(
        'services.updater.requests.get',
        lambda *args, **kwargs: DummyResponse({
            'tag_name': '1.0.1',
            'body': 'Update',
            'assets': [
                {'name': 'Blind_log.exe', 'browser_download_url': 'https://example.com/Blind_log.exe'}
            ]
        })
    )

    result = perform_update_check()

    assert not result.success
    assert result.error


def test_successful_startup_update_closes_the_actual_main_window(monkeypatch):
    from common.utils import Result
    from services import updater

    class FakeFrame:
        def __init__(self):
            self.closed = False

        def IsShown(self):
            return True

        def Close(self):
            self.closed = True

    class FakeApp:
        def __init__(self, frame):
            self.frame = frame
            self.exit_called = False

        def GetTopWindow(self):
            return self.frame

        def ExitMainLoop(self):
            self.exit_called = True

    frame = FakeFrame()
    app = FakeApp(frame)
    monkeypatch.setattr(updater.wx, "GetApp", lambda: app)

    updater._on_download_finished(Result(True), None, None)

    assert frame.closed
    assert not app.exit_called


def test_perform_update_check_handles_malformed_release_tag(monkeypatch):
    monkeypatch.setattr("services.updater.get_version", lambda: "1.0.0")
    monkeypatch.setattr(
        "services.updater.requests.get",
        lambda *args, **kwargs: DummyResponse({
            "tag_name": "release-next",
            "body": "Update",
            "assets": [],
        }),
    )

    result = perform_update_check()

    assert not result.success
    assert result.error


def test_perform_update_check_handles_malformed_current_version(monkeypatch):
    monkeypatch.setattr("services.updater.get_version", lambda: "not-a-version")
    monkeypatch.setattr(
        "services.updater.requests.get",
        lambda *args, **kwargs: DummyResponse({
            "tag_name": "1.0.1",
            "body": "Update",
            "assets": [],
        }),
    )

    result = perform_update_check()

    assert not result.success
    assert result.error
