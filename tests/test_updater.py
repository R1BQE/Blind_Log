import pytest

from updater import perform_update_check


class DummyResponse:
    def __init__(self, data, text=""):
        self._data = data
        self.text = text

    def raise_for_status(self):
        return None

    def json(self):
        return self._data


def test_perform_update_check_returns_result_for_no_update(monkeypatch):
    monkeypatch.setattr('updater.get_version', lambda: '1.0.0')
    monkeypatch.setattr(
        'updater.requests.get',
        lambda *args, **kwargs: DummyResponse({
            'tag_name': '1.0.0',
            'body': 'No changes',
            'assets': [
                {'name': 'Blind_log.zip', 'browser_download_url': 'https://example.com/update.zip'}
            ]
        })
    )

    result = perform_update_check()

    assert result.success
    assert result.data['update_available'] is False
    assert result.data['current_version'] == '1.0.0'


def test_perform_update_check_returns_update_available(monkeypatch):
    monkeypatch.setattr('updater.get_version', lambda: '1.0.0')
    monkeypatch.setattr(
        'updater.requests.get',
        lambda *args, **kwargs: DummyResponse({
            'tag_name': '1.0.1',
            'body': 'Minor fixes',
            'assets': [
                {'name': 'Blind_log.zip', 'browser_download_url': 'https://example.com/update.zip'}
            ]
        })
    )

    result = perform_update_check()

    assert result.success
    assert result.data['update_available'] is True
    assert result.data['latest_version'] == '1.0.1'
    assert result.data['download_url'] == 'https://example.com/update.zip'
