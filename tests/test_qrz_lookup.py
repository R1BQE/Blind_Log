import requests

from localization.i18n import load_translations
from services.qrz_lookup import QRZLookup


def test_qrz_login_does_not_expose_credentials_from_request_exception(monkeypatch):
    load_translations("en")
    secret = "private-password"
    log_messages = []

    def fail_request(*args, **kwargs):
        raise requests.ConnectionError(
            f"Connection failed for https://api.qrz.ru/login?u=operator&p={secret}"
        )

    monkeypatch.setattr("services.qrz_lookup.requests.get", fail_request)
    monkeypatch.setattr("services.qrz_lookup.log_error", log_messages.append)

    result = QRZLookup("operator", secret).login()

    assert not result.success
    assert result.error == (
        "Could not connect to the QRZ.ru server. Check your internet connection."
    )
    assert secret not in result.error
    assert all(secret not in message for message in log_messages)


def test_qrz_lookup_does_not_expose_session_data_from_request_exception(monkeypatch):
    load_translations("en")
    secret = "private-session-id"
    log_messages = []

    def fail_request(*args, **kwargs):
        raise requests.ConnectionError(
            f"Connection failed for https://api.qrz.ru/callsign?id={secret}"
        )

    monkeypatch.setattr("services.qrz_lookup.requests.get", fail_request)
    monkeypatch.setattr("services.qrz_lookup.log_error", log_messages.append)

    lookup = QRZLookup("operator", "password")
    lookup.session_key = secret
    result = lookup.lookup_call("R1BQE")

    assert not result.success
    assert result.error == (
        "Could not connect to the QRZ.ru server. Check your internet connection."
    )
    assert secret not in result.error
    assert all(secret not in message for message in log_messages)
