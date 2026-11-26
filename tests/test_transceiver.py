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
    ("CWR", "CW"), ("FM", "FM"), ("AM", "AM"),
    ("RTTY", "RTTY"), ("MFSK", "MFSK"),
    ("PKTUSB", "MFSK"), ("PKTLSB", "MFSK"),
    ("FT8", None), ("UNKNOWN", None),
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



def test_get_level_reads_numeric_value(monkeypatch):
    client = RigctldClient()
    monkeypatch.setattr(client, "_command", lambda command, line_count=1: ["12.5"])
    assert client.get_level("RFPOWER_METER_WATTS") == 12.5


def test_get_level_rejects_unsupported_level(monkeypatch):
    client = RigctldClient()
    monkeypatch.setattr(client, "_command", lambda command, line_count=1: ["RPRT -11"])
    with pytest.raises(HamlibError, match="cannot read"):
        client.get_level("RFPOWER_METER_WATTS")


def test_set_level_sends_hamlib_command(monkeypatch):
    client = RigctldClient()
    calls = []
    monkeypatch.setattr(
        client, "_command",
        lambda command, line_count=1: calls.append(command) or ["RPRT 0"]
    )
    assert client.set_level("RFPOWER", "0.5") is True
    assert calls == ["L RFPOWER 0.5"]


def test_set_level_rejects_command_injection():
    client = RigctldClient()
    with pytest.raises(HamlibError, match="Invalid Hamlib level value"):
        client.set_level("RFPOWER", "0.5\nF 7100000")


def test_get_power_uses_watt_meter_first(monkeypatch):
    client = RigctldClient()
    calls = []
    def fake_get_level(token):
        calls.append(token)
        if token == "RFPOWER_METER_WATTS":
            return 7.5
        raise HamlibError("unsupported")
    monkeypatch.setattr(client, "get_level", fake_get_level)
    assert client.get_power() == {"token": "RFPOWER_METER_WATTS", "value": 7.5}
    assert calls == ["RFPOWER_METER_WATTS"]


def test_get_power_falls_back_to_generic_meter(monkeypatch):
    client = RigctldClient()
    calls = []
    def fake_get_level(token):
        calls.append(token)
        if token == "RFPOWER_METER_WATTS":
            raise HamlibError("unsupported")
        return 0.42
    monkeypatch.setattr(client, "get_level", fake_get_level)
    assert client.get_power() == {"token": "RFPOWER_METER", "value": 0.42}
    assert calls == ["RFPOWER_METER_WATTS", "RFPOWER_METER"]


def test_get_power_reports_unsupported_meter(monkeypatch):
    client = RigctldClient()
    monkeypatch.setattr(
        client, "get_level",
        lambda token: (_ for _ in ()).throw(HamlibError("unsupported"))
    )
    with pytest.raises(HamlibError, match="POWER_METER_UNSUPPORTED"):
        client.get_power()



def test_get_power_falls_back_to_configured_rfpower(monkeypatch):
    client = RigctldClient()
    calls = []
    def fake_get_level(token):
        calls.append(token)
        if token != "RFPOWER":
            raise HamlibError("unsupported")
        return 0.75
    monkeypatch.setattr(client, "get_level", fake_get_level)
    assert client.get_power() == {"token": "RFPOWER", "value": 0.75}
    assert calls == ["RFPOWER_METER_WATTS", "RFPOWER_METER", "RFPOWER"]



def test_virtual_web_controller_applies_supported_mode_and_bandwidth(monkeypatch):
    from tools.virtual_transceiver_web import RigClient as WebRigClient

    client = WebRigClient()
    commands = []
    monkeypatch.setattr(client, "get_tokens", lambda prefix: ["USB", "PKTUSB"])
    monkeypatch.setattr(
        client, "command",
        lambda command: commands.append(command) or "RPRT 0"
    )
    client.apply("7.1", "PKTUSB", "2400")
    assert commands == ["F 7100000", "M PKTUSB 2400"]


def test_virtual_web_controller_rejects_mode_not_supported_by_hamlib(monkeypatch):
    from tools.virtual_transceiver_web import RigClient as WebRigClient

    client = WebRigClient()
    commands = []
    monkeypatch.setattr(client, "get_tokens", lambda prefix: ["USB", "PKTUSB"])
    monkeypatch.setattr(
        client, "command",
        lambda command: commands.append(command) or "RPRT 0"
    )
    with pytest.raises(ValueError, match="Hamlib"):
        client.apply("7.1", "MFSK", "2000")
    assert commands == []



def test_virtual_web_controller_validates_rfpower_range():
    from tools.virtual_transceiver_web import RigClient as WebRigClient

    client = WebRigClient()
    with pytest.raises(ValueError, match="от 0 до 1"):
        client.set_control("levels", "RFPOWER", "1.5")
