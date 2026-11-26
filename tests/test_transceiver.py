import io
import zipfile

import pytest

from services.transceiver import (
    HamlibError, RigctldClient, TransceiverController, _parse_sha256_checksum,
    _safe_extract, frequency_to_mhz, normalize_mode_for_log,
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


def test_checksum_selects_zip_entry_not_first_hash():
    checksum_text = (
        "a" * 64 + "  hamlib-w64-4.7.2.exe\n"
        + "b" * 64 + "  hamlib-w64-4.7.2.zip\n"
    )
    assert _parse_sha256_checksum(
        checksum_text, "hamlib-w64-4.7.2.zip"
    ) == "b" * 64


def test_checksum_rejects_missing_archive_entry():
    checksum_text = "a" * 64 + "  another-file.zip\n"
    with pytest.raises(HamlibError, match="hamlib-w64-4.7.2.zip"):
        _parse_sha256_checksum(checksum_text, "hamlib-w64-4.7.2.zip")


def test_checksum_accepts_single_bare_hash():
    assert _parse_sha256_checksum("c" * 64, "hamlib-w64-4.7.2.zip") == "c" * 64


def test_dummy_model_starts_without_com_port(monkeypatch):
    from services import transceiver

    captured = {}

    class FakeProcess:
        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        captured["args"] = args
        return FakeProcess()

    monkeypatch.setattr(
        transceiver, "find_hamlib_executable",
        lambda name: "/tmp/hamlib/rigctld.exe"
    )
    monkeypatch.setattr(transceiver.subprocess, "Popen", fake_popen)

    controller = TransceiverController()
    controller.configure({
        "use_hamlib": "1",
        "transceiver_connection": "local",
        "transceiver_model_id": "1",
        "transceiver_com_port": "",
        "transceiver_port": "4532",
    })

    assert "-m" in captured["args"]
    assert captured["args"][captured["args"].index("-m") + 1] == "1"
    assert "-r" not in captured["args"]
    assert "-s" not in captured["args"]
    controller.process = None


def test_physical_model_still_requires_com_port(monkeypatch):
    from services import transceiver

    monkeypatch.setattr(
        transceiver, "find_hamlib_executable",
        lambda name: "/tmp/hamlib/rigctld.exe"
    )
    controller = TransceiverController()
    with pytest.raises(HamlibError, match="COM port"):
        controller.configure({
            "use_hamlib": "1",
            "transceiver_connection": "local",
            "transceiver_model_id": "123",
            "transceiver_com_port": "",
        })
