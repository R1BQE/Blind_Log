import io
import zipfile

import pytest

from services.transceiver import (
    HamlibError, RigctldClient, _safe_extract, frequency_to_mhz,
    normalize_mode_for_log,
)


def test_frequency_is_converted_to_mhz():
    assert frequency_to_mhz(7_100_000) == "7.100000"


@pytest.mark.parametrize(("source", "expected"), [
    ("USB", "SSB"), ("LSB", "SSB"), ("CW", "CW"),
    ("FM", "FM"), ("AM", "AM"), ("FT8", None), ("UNKNOWN", None),
])
def test_mode_mapping(source, expected):
    assert normalize_mode_for_log(source) == expected


def test_frequency_response(monkeypatch):
    client = RigctldClient()
    monkeypatch.setattr(client, "_command", lambda command, line_count=1: ["7100000"])
    assert client.get_frequency() == 7_100_000


def test_mode_response(monkeypatch):
    client = RigctldClient()
    monkeypatch.setattr(client, "_command", lambda command, line_count=1: ["USB", "2400"])
    assert client.get_mode() == {"mode": "USB", "bandwidth": 2400}


def test_invalid_frequency_response_raises(monkeypatch):
    client = RigctldClient()
    monkeypatch.setattr(client, "_command", lambda command, line_count=1: ["RPRT -1"])
    with pytest.raises(HamlibError):
        client.get_frequency()


def test_zip_path_traversal_is_rejected(tmp_path):
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("../outside.txt", "unsafe")
    with pytest.raises(HamlibError, match="unsafe path"):
        _safe_extract(archive.getvalue(), str(tmp_path / "extract"))
